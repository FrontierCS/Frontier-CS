#include <bits/stdc++.h>
using namespace std;

bool try_prefer(const vector<int>& p, vector<int>& assignment, bool prefer_inc) {
  int n = p.size();
  assignment.assign(n, -1);
  vector<int> inc_ends(2, 0);
  vector<int> dec_ends(2, 0);
  int num_inc_used = 0;
  int num_dec_used = 0;
  for (int i = 0; i < n; i++) {
    int x = p[i];
    bool assigned = false;
    int chosen = -1;
    if (prefer_inc) {
      // try append inc
      int best_j = -1;
      int max_e = INT_MIN;
      for (int j = 0; j < 2; j++) {
        if (inc_ends[j] != 0 && inc_ends[j] < x && inc_ends[j] > max_e) {
          max_e = inc_ends[j];
          best_j = j;
        }
      }
      if (best_j != -1) {
        chosen = best_j;
        inc_ends[best_j] = x;
        assigned = true;
      } else {
        // try append dec
        best_j = -1;
        int min_e = INT_MAX;
        for (int j = 0; j < 2; j++) {
          if (dec_ends[j] != 0 && dec_ends[j] > x && dec_ends[j] < min_e) {
            min_e = dec_ends[j];
            best_j = j;
          }
        }
        if (best_j != -1) {
          chosen = 2 + best_j;
          dec_ends[best_j] = x;
          assigned = true;
        } else {
          // start new
          if (num_inc_used < 2) {
            int j = num_inc_used;
            inc_ends[j] = x;
            chosen = j;
            num_inc_used++;
            assigned = true;
          } else if (num_dec_used < 2) {
            int j = num_dec_used;
            dec_ends[j] = x;
            chosen = 2 + j;
            num_dec_used++;
            assigned = true;
          }
        }
      }
    } else {
      // try append dec
      int best_j = -1;
      int min_e = INT_MAX;
      for (int j = 0; j < 2; j++) {
        if (dec_ends[j] != 0 && dec_ends[j] > x && dec_ends[j] < min_e) {
          min_e = dec_ends[j];
          best_j = j;
        }
      }
      if (best_j != -1) {
        chosen = 2 + best_j;
        dec_ends[best_j] = x;
        assigned = true;
      } else {
        // try append inc
        best_j = -1;
        int max_e = INT_MIN;
        for (int j = 0; j < 2; j++) {
          if (inc_ends[j] != 0 && inc_ends[j] < x && inc_ends[j] > max_e) {
            max_e = inc_ends[j];
            best_j = j;
          }
        }
        if (best_j != -1) {
          chosen = best_j;
          inc_ends[best_j] = x;
          assigned = true;
        } else {
          // start new
          if (num_dec_used < 2) {
            int j = num_dec_used;
            dec_ends[j] = x;
            chosen = 2 + j;
            num_dec_used++;
            assigned = true;
          } else if (num_inc_used < 2) {
            int j = num_inc_used;
            inc_ends[j] = x;
            chosen = j;
            num_inc_used++;
            assigned = true;
          }
        }
      }
    }
    if (assigned) {
      assignment[i] = chosen;
    } else {
      return false;
    }
  }
  return true;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  vector<int> p(n);
  for (int &x : p) cin >> x;
  vector<int> assignment;
  bool success = try_prefer(p, assignment, true);
  if (!success) {
    success = try_prefer(p, assignment, false);
  }
  if (!success) {
    assignment.assign(n, 0);
  }
  vector<int> A, B, C, D;
  for (int i = 0; i < n; i++) {
    int ch = assignment[i];
    if (ch == 0) A.push_back(p[i]);
    else if (ch == 1) C.push_back(p[i]);
    else if (ch == 2) B.push_back(p[i]);
    else if (ch == 3) D.push_back(p[i]);
  }
  cout << A.size() << " " << B.size() << " " << C.size() << " " << D.size() << "\n";
  for (int x : A) cout << x << " "; cout << "\n";
  for (int x : B) cout << x << " "; cout << "\n";
  for (int x : C) cout << x << " "; cout << "\n";
  for (int x : D) cout << x << " "; cout << "\n";
  return 0;
}