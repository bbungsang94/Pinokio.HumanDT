import pandas as pd

from utilities.helpers import iou_checker
from utilities.projection_helper import ProjectionManager


class StateMonitor:
    def __init__(self):
        self.Keys = ['In', 'Ready', 'Load_Move', 'Put', 'Empty_Move', 'NA']
        self.Mapper = {'In': '빈 지게차 진입', 'Ready': '지게차 하역준비', 'Load_Move': '지게차 적재이동',
                       'Put': '지게차 1차 하역', 'Empty_Move': '빈 지게차 이동', 'NA': 'N/A'}
        self.Object_list = []
        self.Calculator = dict()
        for key in self.Keys:
            self.Calculator[self.Mapper[key]] = []

    def new_object(self):
        object_name = 'ForkLift_' + str(len(self.Object_list) + 1)
        self.Object_list.append(object_name)
        for key, value in self.Calculator.items():
            value.append(0.0)

    def update_object(self, idx, state, value):
        target = self.Calculator[self.Mapper[state]]
        if len(target) <= idx:
            for itr in range(idx - len(target) + 1):
                self.new_object()
        target[idx] = value

    def cumtime_object(self, idx, state, value):
        self.Calculator[self.Mapper[state]][idx] += value

    def convert_ratio(self):
        temp = pd.DataFrame(self.Calculator, index=self.Object_list)
        transposed = temp.T  # or df1.transpose()
        normalized_df = (transposed - transposed.min()) / (transposed.max() - transposed.min())
        rtn_df = normalized_df.T

        return rtn_df

    def save_file(self, path):
        temp_raw = pd.DataFrame(self.Calculator, index=self.Object_list)
        transposed = temp_raw.T  # or df1.transpose()
        normalized_df = (transposed - transposed.min()) / (transposed.max() - transposed.min())
        ratio_df = normalized_df.T

        temp_raw.to_csv(path + 'raw_data.csv', mode='w', encoding='euc-kr')
        ratio_df.to_csv(path + 'ratio_data.csv', mode='w', encoding='euc-kr')

        # print(self.Calculator)


class StateProcessor:
    def __init__(self):
        self.Linked_state = {'In': ['Ready'],
                             'Ready': ['Load_Move'],
                             'Load_Move': ['Put', 'NA'],
                             'Put': ['Empty_Move'],
                             'Empty_Move': ['In', 'Load_Move'],
                             'NA': ['In', 'Ready', 'Load_Move', 'Put', 'Empty_Move']}
        self.OldStates = dict()
        self.T_now = 0
        self.Monitor = StateMonitor()

    def enqueue(self, idx: int, state: str, pin_name: str):
        (pin_time, _) = pin_name.split('.')
        pin_time = pin_time.replace('-', '.')
        real_time = float(pin_time)
        self.T_now = real_time
        next_state = self.Linked_state[state]
        if idx not in self.OldStates:
            self.Monitor.update_object(idx, state, 0.0)
            self.OldStates[idx] = (state, real_time, next_state)
            return
        else:
            # next state에 해당되는지
            (old_state, old_time, predict_state) = self.OldStates[idx]
            if old_state is 'NA':
                print('과거 NA인데 들어옴')
            self.OldStates[idx] = (state, real_time, next_state)
            if state in predict_state:
                self.Monitor.cumtime_object(idx, old_state, real_time - old_time)
                return
            # Two-step over case
            for candidate_state in predict_state:
                hall_state = self.Linked_state[candidate_state]
                if state in hall_state:
                    self.Monitor.cumtime_object(idx, candidate_state, real_time - old_time)
                    return

    def dequeue(self, idx: int):
        (old_state, old_time, predict_state) = self.OldStates[idx]
        self.Monitor.cumtime_object(idx, old_state, self.T_now - old_time)
        self.OldStates[idx] = ("NA", self.T_now, predict_state)

    def update_time(self, pin_name: str):
        (pin_time, _) = pin_name.split('.')
        pin_time = pin_time.replace('-', '.')
        real_time = float(pin_time)
        self.T_now = real_time
        for key, value in self.OldStates.items():
            (old_state, old_time, predict_state) = value
            self.Monitor.cumtime_object(key, old_state, real_time - old_time)
            self.OldStates[key] = (old_state, real_time, predict_state)

    def save(self, path):
        self.Monitor.save_file(path)


class StateDecisionMaker:
    def __init__(self, output_path, region_info: dict, thr=0.4):
        self.region_info = region_info
        self.Threshold = thr
        self.Processor = StateProcessor()
        self.StateSpace = self.Processor.Monitor.Keys
        self.Ref = ['In', 'Ready', 'Load_Move', 'Put', 'Empty_Move', 'NA']
        self.output_path = output_path

    def get_decision(self, trackers_list: list, boxes_list: list):
        decision_results = []
        for idx, trackers in enumerate(trackers_list):
            for tracker in trackers.get_single_trackers():
                xPt, yPt = ProjectionManager.transform(tracker.box, idx)
                entrance = self.check_entrance(xPt, yPt)
                if iou_checker(tracker.box, boxes_list[idx], thr=self.Threshold):
                    if entrance:
                        tracker_state = ('Ready', tracker.id)
                    else:
                        tracker_state = ('Load_Move', tracker.id)
                else:
                    if entrance:
                        tracker_state = ('In', tracker.id)
                    else:
                        tracker_state = ('Empty_Move', tracker.id)

                decision_results.append(tracker_state)
        return decision_results

    def check_entrance(self, x, y):
        for key, value in self.region_info.items():
            (left, top, right, bottom) = value
            max_y = max(top, bottom)
            min_y = min(top, bottom)
            max_x = max(left, right)
            min_x = min(left, right)
            first_condition = min_x <= x <= max_x
            second_condition = min_y <= y <= max_y
            return first_condition and second_condition

    def loss_tracker(self, trackers_id):
        for single_deleted_list in trackers_id:
            for deleted_id in single_deleted_list:
                self.Processor.dequeue(deleted_id)

        self.Processor.save(self.output_path)

    def update_decision(self, image_name, results):
        for result in results:
            (state, idx) = result
            self.Processor.enqueue(idx, state, image_name)
        self.Processor.update_time(image_name)
