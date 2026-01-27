#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  string S1, S2;
  cin >> S1 >> S2;
  int N = S1.size();
  int M = S2.size();
  auto get_id = [](char ch) -> int {
    if (ch >= '0' && ch <= '9') return ch - '0';
    return 10 + (ch - 'A');
  };
  vector<vector<int>> pos1(36), pos2(36);
  for (int i = 0; i < N; i++) {
    int id = get_id(S1[i]);
    pos1[id].push_back(i);
  }
  for (int j = 0; j < M; j++) {
    int id = get_id(S2[j]);
    pos2[id].push_back(j);
  }
  string Z1 = "";
  Z1.reserve(min(N, M));
  int min_j = 0;
  for (int i = 0; i < N; i++) {
    int id = get_id(S1[i]);
    auto& vec = pos2[id];
    auto it = lower_bound(vec.begin(), vec.end(), min_j);
    if (it != vec.end()) {
      int j = *it;
      Z1 += S1[i];
      min_j = j + 1;
    }
  }
  string Z2 = "";
  Z2.reserve(min(N, M));
  int min_i = 0;
  for (int k = 0; k < M; k++) {
    int id = get_id(S2[k]);
    auto& vec = pos1[id];
    auto it = lower_bound(vec.begin(), vec.end(), min_i);
    if (it != vec.end()) {
      int i_pos = *it;
      Z2 += S2[k];
      min_i = i_pos + 1;
    }
  }
  if (Z1.size() < Z2.size()) {
    Z1 = Z2;
  }
  cout << Z1 << endl;
  return 0;
}