#include <bits/stdc++.h>
using namespace std;

vector<int> do_query(const vector<int>& seq) {
  if (seq.empty()) return {};
  int L = seq.size();
  cout << L;
  for (int u : seq) cout << " " << u;
  cout << '\n';
  cout.flush();
  vector<int> res(L);
  for (int& r : res) cin >> r;
  return res;
}

void output_guess(const vector<int>& perm) {
  cout << -1;
  for (int u : perm) cout << " " << u;
  cout << '\n';
  cout.flush();
  exit(0);
}

int main() {
  int subtask, n;
  cin >> subtask >> n;
  int target_k = (n <= 1000 ? n / 4 : 2000);
  vector<int> labels(n);
  for (int i = 0; i < n; i++) labels[i] = i + 1;
  vector<int> II;
  int s = max(1, n / 20);
  int num_orders = 5;
  vector<int> curr_I;
  int start_pos = 0;
  while (start_pos < n) {
    int bs = min(s, n - start_pos);
    vector<int> batch(labels.begin() + start_pos, labels.begin() + start_pos + bs);
    vector<int> test_seq;
    for (int u : batch) {
      test_seq.push_back(u);
      test_seq.push_back(u);
    }
    auto test_rep = do