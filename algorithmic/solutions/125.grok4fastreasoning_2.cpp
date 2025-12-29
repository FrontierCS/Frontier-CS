#include <bits/stdc++.h>
using namespace std;

int N, total;
vector<char> in_device;
mt19937 rng(random_device{}());

int toggle(int x) {
  cout << "? " << x << '\n';
  cout.flush();
  int r;
  cin >> r;
  in_device[x] = 1 - in_device[x];
  return r;
}

void output_pair(int a, int b) {
  if (a > b) swap(a, b);
  cout << "! " << a << " " << b << '\n';
  cout.flush();
}

void base_solve(vector<int> slices) {
  int sz = slices.size();
  if (sz == 0) return;
  if (sz == 2) {
    int a = slices[0], b = slices[1];
    if (!in_device[a]) toggle(a);
    if (!in_device[b]) toggle(b);
    output_pair(a, b);
    if (in_device[a]) toggle(a);
    if (in_device[b]) toggle(b);
    return;
  }
  // incremental linear scan
  for (int i : slices) {
    if (in_device[i]) toggle(i);
  }
  shuffle(slices.begin(), slices.end(), rng);
  vector<int> U;
  int current_r = 0;
  for (int x : slices) {
    int r_new = toggle(x);
    if (r_new == current_r + 1) {
      U.push_back(x);
      current_r++;
    } else {
      bool found = false;
      for (size_t j = 0; j < U.size(); ++j) {
        int y = U[j];
        int r_after = toggle(y);
        if (r_after == current_r) {
          output_pair(x, y);
          int rr = toggle(x);
          current_r--;
          U.erase(U.begin() + j);
          found = true;
          break;
        } else {
          toggle(y);
        }
      }
      assert(found);
    }
  }
  assert(U.empty());
}

void solve(vector<int> slices) {
  int sz = slices.size();
  if (sz == 0) return;
  if (sz <= 32) {
    base_solve(slices);
    return;
  }
  shuffle(slices.begin(), slices.end(), rng);
  int half = sz / 2;
  vector<int> T1(slices.begin(), slices.begin() + half);
  vector<int> T2(slices.begin() + half, slices.end());
  // process T1
  int r1 = 0;
  for (size_t ii = 0; ii < T1.size(); ++ii) {
    int i = T1[ii];
    int rr = toggle(i);
    if (ii == T1.size() - 1) r1 = rr;
  }
  vector<int> P1;
  for (int z : T1) {
    int r_after = toggle(z);
    bool single = (r_after == r1 - 1);
    int dummy = toggle(z);
    if (!single) P1.push_back(z);
  }
  vector<char> is_p(total + 1, 0);
  for (int z : P1) is_p[z] = 1;
  vector<int> S1;
  for (int z : T1) if (!is_p[z]) S1.push_back(z);
  for (int i : S1) toggle(i);
  solve(P1);
  // process T2
  int r2 = 0;
  for (size_t ii = 0; ii < T2.size(); ++ii) {
    int i = T2[ii];
    int rr = toggle(i);
    if (ii == T2.size() - 1) r2 = rr;
  }
  vector<int> P2;
  for (int z : T2) {
    int r_after = toggle(z);
    bool single = (r_after == r2 - 1);
    int dummy = toggle(z);
    if (!single) P2.push_back(z);
  }
  vector<char> is_p2(total + 1, 0);
  for (int z : P2) is_p2[z] = 1;
  vector<int> S2;
  for (int z : T2) if (!is_p2[z]) S2.push_back(z);
  for (int i : S2) toggle(i);
  solve(P2);
  // T'
  vector<int> Tp = S1;
  Tp.insert(Tp.end(), S2.begin(), S2.end());
  for (int i : Tp) toggle(i);
  solve(Tp);
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  cin >> N;
  total = 2 * N;
  in_device.assign(total + 1, 0);
  vector<int> initial(total);
  for (int i = 0; i < total; ++i) initial[i] = i + 1;
  solve(initial);
  return 0;
}