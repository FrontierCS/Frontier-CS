#include <bits/stdc++.h>
using namespace std;

int N;
vector<vector<int>> Mat;
vector<int> Perm;
vector<bool> Used;
bool found;
int CurChanges;
int LastC;

void dfs(int pos) {
  if (found) return;
  if (pos == N) {
    int cn = Mat[Perm[N - 1]][Perm[0]];
    int last_c = Mat[Perm[N - 2]][Perm[N - 1]];
    int added = (last_c != cn ? 1 : 0);
    if (CurChanges + added <= 1) {
      found = true;
    }
    return;
  }
  for (int cand = 1; cand <= N; ++cand) {
    if (Used[cand]) continue;
    Used[cand] = true;
    Perm[pos] = cand;
    bool can_continue = true;
    int new_added = 0;
    int this_c = 0;
    if (pos > 0) {
      this_c = Mat[Perm[pos - 1]][cand];
      if (pos > 1) {
        int prev_c = Mat[Perm[pos - 2]][Perm[pos - 1]];
        if (prev_c != this_c) new_added = 1;
      }
      int temp_c = CurChanges + new_added;
      if (temp_c > 1) can_continue = false;
    }
    if (can_continue) {
      int old_cur = CurChanges;
      int old_last = LastC;
      CurChanges += new_added;
      LastC = this_c;
      dfs(pos + 1);
      CurChanges = old_cur;
      LastC = old_last;
    }
    Used[cand] = false;
    if (found) return;
  }
}

int main() {
  while (cin >> N) {
    Mat.assign(N + 1, vector<int>(N + 1, 0));
    for (int i = 1; i <= N; ++i) {
      for (int j = 1; j <= N; ++j) {
        cin >> Mat[i][j];
      }
    }
    Perm.resize(N);
    Used.assign(N + 1, false);
    found = false;
    CurChanges = 0;
    LastC = -1;
    dfs(0);
    if (found) {
      for (int i = 0; i < N; ++i) {
        if (i > 0) cout << " ";
        cout << Perm[i];
      }
      cout << endl;
    } else {
      cout << -1 << endl;
    }
  }
  return 0;
}