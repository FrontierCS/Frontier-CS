#include <bits/stdc++.h>

using namespace std;

int n, k;

char ask(int c) {
  cout << "? " << c << endl;
  cout.flush();
  char ch;
  cin >> ch;
  return ch;
}

void res() {
  cout << "R" << endl;
  cout.flush();
}

pair<int, vector<int>> solve(int l, int r) {
  int len = r - l + 1;
  if (len <= k) {
    res();
    vector<int> reps;
    int cnt = 0;
    for (int i = l; i <= r; i++) {
      char ch = ask(i);
      if (ch == 'N') {
        cnt++;
        reps.push_back(i);
      }
    }
    return {cnt, reps};
  }
  int mid = (l + r) / 2;
  auto [dl, rl] = solve(l, mid);
  auto [dr, rr] = solve(mid + 1, r);
  int ii = 0;
  vector<int> small, large_reps;
  bool l_small = dl <= dr;
  if (l_small) {
    small = rl;
    large_reps = rr;
  } else {
    small = rr;
    large_reps = rl;
  }
  int ds = small.size();
  if (ds <= k) {
    res();
    for (int p : small) {
      ask(p);
    }
    for (int p : large_reps) {
      char ch = ask(p);
      if (ch == 'Y') ii++;
      if (p != large_reps.back()) {
        for (int q : small) {
          ask(q);
        }
      }
    }
  } else {
    ii = 0;
  }
  int d = dl + dr - ii;
  vector<int> union_reps = rl;
  union_reps.insert(union_reps.end(), rr.begin(), rr.end());
  return {d, union_reps};
}

int main() {
  cin >> n >> k;
  auto [d, reps] = solve(1, n);
  cout << "! " << d << endl;
  cout.flush();
  return 0;
}