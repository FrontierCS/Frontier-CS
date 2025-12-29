#include <bits/stdc++.h>
using namespace std;

int n;

vector<int> do_query(const vector<int>& ops) {
  int L = ops.size();
  cout << L;
  for (int x : ops) {
    cout << " " << x;
  }
  cout << endl;
  cout.flush();
  vector<int> res(L);
  for (int &r : res) {
    cin >> r;
  }
  return res;
}

vector<int> get_neighbors(int center, const vector<int>& tests, bool already_lit) {
  vector<int> ops;
  int num = tests.size();
  if (!already_lit) {
    ops.push_back(center);
  }
  vector<int> after_add_indices(num);
  for (int i = 0; i < num; ++i) {
    int global_idx = ops.size();
    ops.push_back(tests[i]);
    after_add_indices[i] = global_idx;
    ops.push_back(tests[i]);
  }
  vector<int> responses = do_query(ops);
  vector<int> neigh;
  for (int i = 0; i < num; ++i) {
    int resp = responses[after_add_indices[i]];
    if (resp == 1) {
      neigh.push_back(tests[i]);
    }
  }
  return neigh;
}

int main() {
  int subtask;
  cin >> subtask >> n;
  vector<int> all_tests;
  for (int i = 1; i <= n; ++i) {
    if (i != 1) all_tests.push_back(i);
  }
  vector<int> adj1 = get_neighbors(1, all_tests, false);
  int small = min(adj1[0], adj1[1]);
  int large = max(adj1[0], adj1[1]);
  vector<int> trans_ops = {small, 1};
  do_query(trans_ops);
  vector<int> perm = {1, small};
  set<int> usedd = {1, small};
  vector<int> remaining;
  for (int i = 1; i <= n; ++i) {
    if (usedd.find(i) == usedd.end()) {
      remaining.push_back(i);
    }
  }
  vector<int> pos(n + 1, -1);
  for (int i = 0; i < remaining.size(); ++i) {
    pos[remaining[i]] = i;
  }
  int current = small;
  while (!remaining.empty()) {
    vector<int> adj = get_neighbors(current, remaining, true);
    int next_one = adj[0];
    int idx = pos[next_one];
    int last = remaining.back();
    remaining[idx] = last;
    pos[last] = idx;
    remaining.pop_back();
    pos[next_one] = -1;
    perm.push_back(next_one);
    usedd.insert(next_one);
    current = next_one;
  }
  cout << -1;
  for (int p : perm) {
    cout << " " << p;
  }
  cout << endl;
  cout.flush();
  return 0;
}