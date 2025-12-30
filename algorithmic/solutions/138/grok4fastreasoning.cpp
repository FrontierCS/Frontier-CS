#include <bits/stdc++.h>
using namespace std;

int get_id(char c) {
  if (c >= 'a' && c <= 'z') return c - 'a';
  if (c >= 'A' && c <= 'Z') return 26 + (c - 'A');
  if (c >= '0' && c <= '9') return 52 + (c - '0');
  assert(false);
  return -1;
}

char get_char(int id) {
  if (id < 26) return 'a' + id;
  if (id < 52) return 'A' + (id - 26);
  return '0' + (id - 52);
}

string make_key(const vector<int>& counts) {
  string s(62, 0);
  for (int i = 0; i < 62; i++) s[i] = char(counts[i]);
  return s;
}

int main() {
  int n, m, k;
  cin >> n >> m >> k;
  vector<string> init_grid(n);
  for (int i = 0; i < n; i++) cin >> init_grid[i];
  vector<string> targ_grid(n);
  for (int i = 0; i < n