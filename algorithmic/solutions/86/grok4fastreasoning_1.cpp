#include <bits/stdc++.h>
using namespace std;

int n;

int query(int a, int b, int c) {
  cout << 0 << " " << a << " " << b << " " << c << endl;
  cout.flush();
  int res;
  cin >> res;
  return res;
}

void output(vector<pair<int,int>> edges) {
  cout << 1;
  for (auto p : edges) {
    cout << " " << p.first << " " << p.second;
  }
  cout << endl;
  cout.flush();
  exit(0);
}

void reconstruct(vector<int> S, int r, vector<pair<int,int>>& edges) {
  int ss = S.size();
  if (ss <= 1) return;
  if (ss == 2) {
    int other = (S[0] == r ? S[1] : S[0]);
    edges.emplace_back(r, other);
    return;
  }
  srand(time(0) + clock());
  int best_k =