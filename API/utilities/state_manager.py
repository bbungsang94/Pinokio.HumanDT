import math

import pandas as pd

from utilities.helpers import iou_checker
from utilities.projection_helper import ProjectionManager


class StateMonitor:
    def __init__(self):
        self.Keys = ['In', 'Ready', 'Load_Move', 'Put', 'Empty_Move', 'NA', 'Dist', 'Dock_Count']
        self.Mapper = {'In': '도크 진입', 'Ready': '트레일러 작업', 'Load_Move': '지게차 적재이동',
                       'Put': '1차 하역', 'Empty_Move': '빈 지게차 이동', 'NA': 'N/A', 'Dist': '이동 거리',
                       'Dock_Count': '도크 작업 수'}
        self.Object_list = []
        self.Calculator = dict()
        for key in self.Keys:
            self.Calculator[self.Mapper[key]] = []

    def new_object(self):
        object_name = 'ForkLift_' + str(len(self.Object_list))
        self.Object_list.append(object_name)
        for key, value in self.Calculator.items():
            value.append(0.0)

    def update_object(self, idx, state, value):
        target = self.Calculator[self.Mapper[state]]
        if len(target) <= idx:
            for itr in range(idx - len(target) + 1):
                self.new_object()
        target[idx] = value

    def update_distance(self, idx, value):
        self.Calculator[self.Mapper['Dist']][idx] += value

    def update_dock_count(self, dock_id, value):
        self.update_object(dock_id, 'Dock_Count', value)

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
                             'Ready': ['Load_Move', 'Empty_Move'],
                             'Load_Move': ['In', 'Put', 'NA'],
                             'Put': ['Empty_Move'],
                             'Empty_Move': ['In', 'Load_Move', 'NA'],
                             'NA': ['Load_Move', 'Empty_Move']}
        self.Predict_state = {"In": (["Empty_Move", "Load_Move"], "Ready"),
                              "Load_Move": (["Empty_Move"], "Put"),
                              "Load_Move Empty_Move": (["Ready"], "In")}
        self.OldStates = dict()
        self.T_now = 0
        self.Monitor = StateMonitor()

    def enqueue(self, states: tuple, pin_name: str, idx, distance, dock_info):
        (pin_time, _) = pin_name.split('.')
        pin_time = pin_time.replace('-', '.')
        real_time = float(pin_time)
        self.T_now = real_time
        (state, warning,) = states
        next_state = self.Linked_state[state]
        if idx not in self.OldStates:
            self.Monitor.update_object(idx, state, 0.0)
            self.Monitor.update_distance(idx, distance)
            for dock_id, dock_count in dock_info.items():
                self.Monitor.update_dock_count(dock_id, dock_count)
            self.OldStates[idx] = (state, real_time, next_state)
            return
        else:
            # next state에 해당되는지
            (old_state, old_time, predict_state) = self.OldStates[idx]
            if warning:
                if old_state == "In":
                    return
            if state in predict_state:
                self.Monitor.cumtime_object(idx, old_state, real_time - old_time)
                self.Monitor.update_distance(idx, distance)
                for dock_id, dock_count in dock_info.items():
                    self.Monitor.update_dock_count(dock_id, dock_count)
                self.OldStates[idx] = (state, real_time, next_state)
                return
            # Two-step over case
            for key in self.Predict_state.keys():
                if old_state in key:
                    (two_step_states, next_step) = self.Predict_state[key]
                    if state in two_step_states:
                        self.Monitor.cumtime_object(idx, next_step, real_time - old_time)
                        self.Monitor.update_distance(idx, distance)
                        for dock_id, dock_count in dock_info.items():
                            self.Monitor.update_dock_count(dock_id, dock_count)
                        self.OldStates[idx] = (state, real_time, next_state)
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

    def enqueue_dist(self, idx: int, dist: float):
        self.Monitor.update_distance(idx, dist)

    def save(self, path):
        self.Monitor.save_file(path)


class StateDecisionMaker:
    def __init__(self, output_path, dock_info: dict, thr=0.4):
        self.dock_info = dock_info
        self.Threshold = thr
        self.Processor = StateProcessor()
        self.StateSpace = self.Processor.Monitor.Keys
        self.Ref = ['In', 'Ready', 'Load_Move', 'Put', 'Empty_Move', 'NA']
        self.output_path = output_path
        self.dock_count = dict()
        for dock_id in self.dock_info.keys():
            self.dock_count[dock_id] = 0

    def get_decision(self, trackers_list: dict, boxes_list: list):
        decision_results = []
        state_trackers = []
        distance_results = dict()
        dock_info_results = []
        for idx, trackers in trackers_list.items():
            for tracker in trackers:
                xPt, yPt = ProjectionManager.transform(tracker.box, idx)
                if 357 < yPt < 380:
                    if 140 < xPt:
                        test = True
                entrance, warning, (dockIn, dockId) = self.check_entrance(xPt, yPt)
                tracker.dockNumber = dockId
                if len(tracker.history) <= 1:
                    dist = 0
                else:
                    pre_x = tracker.history[-1][0] - tracker.history[-2][0]
                    pre_y = tracker.history[-1][1] - tracker.history[-2][1]
                    pre_dist = math.sqrt(pre_x ** 2 + pre_y ** 2)
                    x = xPt - tracker.history[-1][0]
                    y = yPt - tracker.history[-1][1]
                    dist = math.sqrt(x ** 2 + y ** 2)
                    if pre_dist + 1 < dist:
                        dist = 0
                if entrance == "Move":
                    if iou_checker(tracker.box, boxes_list[idx], thr=self.Threshold):
                        state = ("Load_Move", warning)
                    else:
                        state = ("Empty_Move", warning)
                else:
                    state = (entrance, warning)

                tracker.state = state
                tracker_state = (state, tracker.id)
                dock_info = (dockId, dockIn, tracker)
                decision_results.append(tracker_state)
                dock_info_results.append(dock_info)
                distance_results[tracker] = dist
                state_trackers.append((idx, state, tracker))
        return decision_results, distance_results, state_trackers, dock_info_results

    def check_entrance(self, x, y):
        warning = False
        dock_info = (False, 0)
        rtn = "", warning, dock_info
        for dock_id, value in self.dock_info.items():
            (left, top, right, bottom) = value
            max_y = max(top, bottom)
            min_y = min(top, bottom)
            max_x = max(left, right)
            min_x = min(left, right)
            first_condition = min_x <= x <= max_x
            second_condition = min_y <= y <= max_y
            enter = first_condition and second_condition
            if not enter:
                if min_x - ((max_x - min_x) / 2) < x < max_x + ((max_x - min_x) / 2):
                    warning = True
                if x > max_x and second_condition:
                    return "Ready", warning, dock_info
                else:
                    rtn = "Move", warning, dock_info
            else:
                dock_info = (True, dock_id)
                return "In", False, dock_info
        return rtn

    def loss_tracker(self, trackers_id, image_name):
        # Something Value -> NA
        if isinstance(trackers_id, list):
            self.Processor.update_time(image_name)
        # Needs Dequeue
        elif isinstance(trackers_id, dict):
            for single_deleted_list in trackers_id.values():
                for deleted_id in single_deleted_list:
                    self.Processor.dequeue(deleted_id)

    def update_decision(self, image_name, results):
        for result in results:
            (idx, states, tracker, distance) = result
            self.Processor.enqueue(states, image_name, idx, distance, self.dock_count)
        self.Processor.update_time(image_name)
        self.Processor.save(self.output_path)
