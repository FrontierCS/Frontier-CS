#include <bits/stdc++.h>
using namespace std;

int N, R, S;
vector<pair<int,int>> conn;
vector<vector<int>> users;
vector<char> ans;

int query(const string& st) {
  cout << "? " << st << endl;
  fflush(stdout);
  int res;
  cin >> res;
  return res;
}

void force(string& state, int node, int val) {
  if (node >= N) {
    state[node] = '0' + val;
    return;
  }
  state[node] = '0';
  auto [u, v] = conn[node];
  force(state, u, val);
  force(state, v, val);
}

void determine(int j) {
  if (j >= N) return;
  if (ans[j] != '\0') return;
  string state(S, '0');
  auto [uu, vv] = conn[j];
  force(state, uu, 0);
  force(state, vv, 1);
  // path
  vector<int> path_anc;
  int curr = j;
  while (curr != 0) {
    const auto& us = users[curr];
    if (us.empty()) break;
    int next = us[0];
    path_anc.push_back(next);
    curr = next;
  }
  int prev_c = j;
  for (int k : path_anc) {
    auto [u1, u2] = conn[k];
    int sib = (u1 == prev_c ? u2 : u1);
    int qv = (ans[k] == '&' ? 1 : 0);
    force(state, sib, qv);
    prev_c = k;
  }
  int b = query(state);
  ans[j] = (b ? '|' : '&');
  determine(uu);
  determine(vv);
}

int main() {
  cin >> N >> R;
  S = 2 * N + 1;
  conn.resize(N);
  users.assign(S, {});
  for (int i = 0; i < N; i++) {
    int u, v;
    cin >> u >> v;
    conn[i] = {u, v};
    users[u].push_back(i);
    users[v].push_back(i);
  }
  ans.assign(N, '\0');
  determine(0);
  string t;
  for (char c : ans) t += c;
  cout << "! " << t << endl;
  fflush(stdout);
  return 0;
}