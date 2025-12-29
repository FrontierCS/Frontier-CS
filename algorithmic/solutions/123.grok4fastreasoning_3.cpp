#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int n;
  cin >> n;
  vector<vector<char>> inS(54, vector<char>(n + 1, 0));
  vector<int> is_yes(54, 0);
  int current_k = 0;
  vector<int> curr_possible;
  while (true) {
    curr_possible.clear();
    for (int y = 1; y <= n; y++) {
      bool ok = true;
      int last_err = -2;
      for (int q = 1; q <= current_k; q++) {
        bool true_mem = (inS[q][y] != 0);
        bool rec_yes = (is_yes[q] != 0);
        bool err = (true_mem != rec_yes);
        if (err && last_err == q - 1) {
          ok = false;
          break;
        }
        if (err) last_err = q;
      }
      if (ok) curr_possible.push_back(y);
    }
    int sz = curr_possible.size();
    if (sz == 0) {
      printf("! 1\n");
      fflush(stdout);
      return 0;
    }
    if (sz == 1) {
      int g = curr_possible[0];
      printf("! %d\n", g);
      fflush(stdout);
      string resp;
      cin >> resp;
      return 0;
    }
    if (sz == 2) {
      int g1 = curr_possible[0], g2 = curr_possible[1];
      printf("! %d\n", g1);
      fflush(stdout);
      string resp;
      cin >> resp;
      if (resp == ":)") return 0;
      printf("! %d\n", g2);
      fflush(stdout);
      cin >> resp;
      return 0;
    }
    if (current_k >= 53) {
      int g1 = curr_possible[0], g2 = curr_possible[1];
      printf("! %d\n", g1);
      fflush(stdout);
      string resp;
      cin >> resp;
      if (resp == ":)") return 0;
      printf("! %d\n", g2);
      fflush(stdout);
      cin >> resp;
      return 0;
    }
    current_k++;
    int split = sz / 2;
    int idx = split - 1;
    int m = curr_possible[idx];
    printf("? %d", m);
    for (int i = 1; i <= m; i++) {
      printf(" %d", i);
    }
    printf("\n");
    fflush(stdout);
    for (int i = 1; i <= m; i++) inS[current_k][i] = 1;
    string ans_str;
    cin >> ans_str;
    is_yes[current_k] = (ans_str == "YES" ? 1 : 0);
  }
  return 0;
}