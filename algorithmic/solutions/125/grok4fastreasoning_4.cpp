#include <bits/stdc++.h>
using namespace std;

int N;

void solve_bipartite(vector<int> left, vector<int> right) {
  int cs = left.size();
  if (cs == 0) return;
  if (cs == 1) {
    int a = left[0], b = right[0];
    if (a > b) swap(a, b);
    cout << "! " << a << " " << b << endl;
    fflush(stdout);
    return;
  }
  int h = cs / 2;
  vector<int> right1(right.begin(), right.begin() + h);
  vector<int> right2(right.begin() + h, right.end());
  vector<int> l1, l2;
  int prev_r = 0;
  for (int x : left) {
    cout << "? " << x << endl;
    fflush(stdout);
    int nr;
    cin >> nr;
    prev_r = nr;
  }
  for (int x : right1) {
    cout << "? " << x << endl;
    fflush(stdout);
    int nr;
    cin >> nr;
    prev_r = nr;
  }
  for (int x : left) {
    cout << "? " << x << endl;
    fflush(stdout);
    int nr;
    cin >> nr;
    int del = nr - prev_r;
    if (del == 0) {
      l1.push_back(x);
    } else {
      l2.push_back(x);
    }
    prev_r = nr;
  }
  for (int x : right1) {
    cout << "? " << x << endl;
    fflush(stdout);
    int nr;
    cin >> nr;
    prev_r = nr;
  }
  solve_bipartite(l1, right1);
  solve_bipartite(l2, right2);
}

void solve_general(vector<int> group) {
  int sz = group.size();
  if (sz == 0) return;
  if (sz == 2) {
    int a = group[0], b = group[1];
    if (a > b) swap(a, b);
    cout << "! " << a << " " << b << endl;
    fflush(stdout);
    return;
  }
  int half = sz / 2;
  vector<int> L(group.begin(), group.begin() + half);
  vector<int> R(group.begin() + half, group.end());
  vector<int> order_L = L;
  sort(order_L.begin(), order_L.end());
  vector<int> G_L;
  int prev_r = 0;
  for (int x : order_L) {
    cout << "? " << x << endl;
    fflush(stdout);
    int nr;
    cin >> nr;
    int del = nr - prev_r;
    if (del == 0) G_L.push_back(x);
    prev_r = nr;
  }
  vector<int> order_R = R;
  sort(order_R.begin(), order_R.end());
  vector<int> K;
  for (int x : order_R) {
    cout << "? " << x << endl;
    fflush(stdout);
    int nr;
    cin >> nr;
    int del = nr - prev_r;
    if (del == 0) K.push_back(x);
    prev_r = nr;
  }
  vector<int> I;
  for (int x : order_R) {
    cout << "? " << x << endl;
    fflush(stdout);
    int nr;
    cin >> nr;
    int del = nr - prev_r;
    if (del == -1) I.push_back(x);
    prev_r = nr;
  }
  set<int> set_I(I.begin(), I.end());
  vector<int> B;
  for (int x : K) {
    if (set_I.count(x) == 0) B.push_back(x);
  }
  vector<int> D1_L;
  for (int x : order_L) {
    cout << "? " << x << endl;
    fflush(stdout);
    int nr;
    cin >> nr;
    int del = nr - prev_r;
    if (del == -1) D1_L.push_back(x);
    prev_r = nr;
  }
  set<int> set_G(G_L.begin(), G_L.end());
  vector<int> A;
  for (int x : D1_L) {
    if (set_G.count(x) == 0) A.push_back(x);
  }
  solve_bipartite(A, B);
  set<int> set_A(A.begin(), A.end());
  vector<int> L_int;
  for (int x : L) {
    if (set_A.count(x) == 0) L_int.push_back(x);
  }
  solve_general(L_int);
  set<int> set_B(B.begin(), B.end());
  vector<int> R_int;
  for (int x : R) {
    if (set_B.count(x) == 0) R_int.push_back(x);
  }
  solve_general(R_int);
}

int main() {
  cin >> N;
  vector<int> initial;
  for (int i = 1; i <= 2 * N; i++) initial.push_back(i);
  solve_general(initial);
  return 0;
}