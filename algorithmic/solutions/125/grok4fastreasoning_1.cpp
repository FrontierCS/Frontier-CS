#include <bits/stdc++.h>

using namespace std;

int N;

int query(int x) {
  cout << "? " << x << endl;
  fflush(stdout);
  int r;
  cin >> r;
  return r;
}

void output_pair(int a, int b) {
  if (a > b) swap(a, b);
  cout << "! " << a << " " << b << endl;
  fflush(stdout);
}

vector<pair<int, int>> match_unbalanced(vector<int> left, vector<int>& right) {
  int l = left.size();
  int d = right.size();
  vector<pair<int, int>> res;
  if (l == 0) return res;
  if (l == 1) {
    int s = left[0];
    int curr_r = query(s);
    vector<int> remaining;
    int expected = 1;
    for (size_t i = 0; i < right.size(); ++i) {
      int x = right[i];
      int rr = query(x);
      if (rr == expected) {
        output_pair(s, x);
        res.emplace_back(s, x);
        query(x); // remove x
      } else {
        query(x); // remove x
        remaining.push_back(x);
      }
      expected = 1;
    }
    query(s); // remove s
    right