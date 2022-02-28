import pandas as pd


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

    def save(self, path):
        self.Monitor.save_file(path)
        print(self.Monitor.Calculator)