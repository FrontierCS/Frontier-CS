#include <bits/stdc++.h>
using namespace std;

bool check_covered(int idx, char mat[][20], const vector<string>& S, int N) {
  string s = S[idx];
  int k = s.size();
  for (int dir = 0; dir < 2; dir++) {
    for (int fix = 0; fix < N; fix++) {
      for (int st = 0; st < N; st++) {
        bool match = true;
        for (int p = 0; p < k; p++) {
          int i = (dir == 0 ? fix : (st + p) % N);
          int j = (dir == 0 ? (st + p) % N : fix);
          if (mat[i][j] != s[p]) {
            match = false;
            break;
          }
        }
        if (match) return true;
      }
    }
  }
  return false;
}

int compute_c(char mat[][20], const vector<string>& S, int M, int N) {
  int cc = 0;
  for (int i = 0; i < M; i++) {
    if (check_covered(i, mat, S, N)) cc++;
  }
  return cc;
}

int main() {
  int N, M;
  cin >> N >> M;
  vector<string> S(M);
  for (int i = 0; i < M; i++) cin >> S[i];
  vector<int> order(M);
  iota(order.begin(), order.end(), 0);
  sort(order.begin(), order.end(), [&](int a, int b) {
    if (S[a].size() != S[b].size()) return S[a].size() > S[b].size();
    return a < b;
  });
  char mat[20][20];
  for (int i = 0; i < N; i++)
    for (int j = 0; j < N; j++) mat[i][j] = '.';
  vector<vector<vector<int>>> covering(N, vector<vector<int>>(N));
  for (int oi = 0; oi < M; oi++) {
    int idx = order[oi];
    string s = S[idx];
    int k = s.size();
    int best_numdot = k + 1;
    int best_dir = -1, best_fix = -1, best_start = -1;
    for (int dir = 0; dir < 2; dir++) {
      for (int fix = 0; fix < N; fix++) {
        for (int st = 0; st < N; st++) {
          int conf = 0;
          int numdot = 0;
          for (int p = 0; p < k; p++) {
            int i = (dir == 0 ? fix : (st + p) % N);
            int j = (dir == 0 ? (st + p) % N : fix);
            char curr = mat[i][j];
            if (curr != '.' && curr != s[p]) conf++;
            if (curr == '.') numdot++;
          }
          if (conf == 0 && numdot < best_numdot) {
            best_numdot = numdot;
            best_dir = dir;
            best_fix = fix;
            best_start = st;
          }
        }
      }
    }
    if (best_numdot <= k) {
      int dir = best_dir, fix = best_fix, st = best_start;
      for (int p = 0; p < k; p++) {
        int i = (dir == 0 ? fix : (st + p) % N);
        int j = (dir == 0 ? (st + p) % N : fix);
        if (mat[i][j] == '.') {
          mat[i][j] = s[p];
        }
        covering[i][j].push_back(idx);
      }
    }
  }
  // first compute c
  int c = compute_c(mat, S, M, N);
  // uncovered
  vector<int> uncovered;
  for (int i = 0; i < M; i++) {
    if (!check_covered(i, mat, S, N)) uncovered.push_back(i);
  }
  // sort uncovered
  sort(uncovered.begin(), uncovered.end(), [&](int a, int b) {
    if (S[a].size() != S[b].size()) return S[a].size() > S[b].size();
    return a < b;
  });
  // second phase
  for (int uu : uncovered) {
    int idx = uu;
    string s = S[idx];
    int k = s.size();
    int min_cost = INT_MAX / 2;
    int bdir = -1, bfix = -1, bst = -1;
    for (int dir = 0; dir < 2; dir++) {
      for (int fix = 0; fix < N; fix++) {
        for (int st = 0; st < N; st++) {
          int cost = 0;
          for (int p = 0; p < k; p++) {
            int i = (dir == 0 ? fix : (st + p) % N);
            int j = (dir == 0 ? (st + p) % N : fix);
            char curr = mat[i][j];
            char req = s[p];
            if (curr != '.' && curr != req) {
              cost += (int)covering[i][j].size();
            }
          }
          if (cost < min_cost) {
            min_cost = cost;
            bdir = dir;
            bfix = fix;
            bst = st;
          }
        }
      }
    }
    if (min_cost <= 5) {
      int dir = bdir, fix = bfix, st = bst;
      for (int p = 0; p < k; p++) {
        int i = (dir == 0 ? fix : (st + p) % N);
        int j = (dir == 0 ? (st + p) % N : fix);
        mat[i][j] = s[p];
      }
    }
  }
  // now compute final_c
  int final_c = compute_c(mat, S, M, N);
  // if not all covered, fill with most common char
  if (final_c < M) {
    map<char, int> freq;
    for (const auto& str : S)
      for (char ch : str) freq[ch]++;
    char fill_char = 'A';
    int maxf = -1;
    for (auto& p : freq) {
      if (p.second > maxf) {
        maxf = p.second;
        fill_char = p.first;
      }
    }
    for (int i = 0; i < N; i++)
      for (int j = 0; j < N; j++)
        if (mat[i][j] == '.') mat[i][j] = fill_char;
  }
  // output
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      cout << mat[i][j];
    }
    cout << endl;
  }
  return 0;
}