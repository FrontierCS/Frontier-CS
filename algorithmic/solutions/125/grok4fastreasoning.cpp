#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N;
  cin >> N;
  int total = 2 * N;
  vector<int> all(total);
  for (int i = 0; i < total; i++) all[i] = i + 1;
  vector<char> inside(total + 1, 0);
  auto toggle = [&](int x, int& r) {
    cout << "? " << x << endl;
    cout.flush();
    cin >> r;
    inside[x] = 1 - inside[x];
  };
  auto general = [&](auto&& self, vector<int> UU) -> void {
    size_t s = UU.size();
    if (s == 0) return;
    if (s == 2) {
      int a = UU[0], b = UU[1];
      cout << "! " << a << " " << b << endl;
      cout.flush();
      int d;
      if (inside[a]) toggle(a, d);
      if (inside[b]) toggle(b, d);
      return;
    }
    size_t half = s / 2;
    vector<int> L(UU.begin(), UU.begin() + half);
    vector<int> R(UU.begin() + half, UU.end());
    // set S = L
    int current_r;
    for (int x : L) {
      toggle(x, current_r);
    }
    // test L
    vector<int> L_int, Cross_L;
    for (int x : L) {
      int new_r;
      toggle(x, new_r); // out
      bool cross = (new_r == current_r - 1);
      int back_r;
      toggle(x, back_r); // in
      if (cross) Cross_L.push_back(x);
      else L_int.push_back(x);
    }
    // clear L
    for (int x : L) {
      int rr;
      toggle(x, rr); // out
    }
    // set S = R
    for (int y : R) {
      toggle(y, current_r);
    }
    // test R
    vector<int> R_int, Cross_R;
    for (int y : R) {
      int new_r;
      toggle(y, new_r); // out
      bool cross = (new_r == current_r - 1);
      int back_r;
      toggle(y, back_r); // in
      if (cross) Cross_R.push_back(y);
      else R_int.push_back(y);
    }
    // clear R
    for (int y : R) {
      int rr;
      toggle(y, rr); // out
    }
    // recurse
    self(self, L_int);
    self(self, R_int);
    // bipartite
    auto bipartite = [&](auto&& bself, vector<int> AA, vector<int> BB) -> void {
      size_t mm = AA.size();
      if (mm == 0) return;
      if (mm == 1) {
        int a = AA[0], b = BB[0];
        cout << "! " << a << " " << b << endl;
        cout.flush();
        int d;
        if (inside[a]) toggle(a, d);
        if (inside[b]) toggle(b, d);
        return;
      }
      size_t hhalf = mm / 2;
      vector<int> A1(AA.begin(), AA.begin() + hhalf);
      vector<int> A2(AA.begin() + hhalf, AA.end());
      // set S = A1
      int curr_r;
      for (int x : A1) {
        toggle(x, curr_r);
      }
      // test B
      vector<int> B1, B2;
      for (int y : BB) {
        int new_r;
        toggle(y, new_r); // in
        bool toA1 = (new_r == curr_r);
        int back_r;
        toggle(y, back_r); // out
        if (toA1) B1.push_back(y);
        else B2.push_back(y);
      }
      // clear A1
      for (int x : A1) {
        int rr;
        toggle(x, rr); // out
      }
      bself(bself, A1, B1);
      bself(bself, A2, B2);
    };
    bipartite(bipartite, Cross_L, Cross_R);
  };
  general(general, all);
  return 0;
}