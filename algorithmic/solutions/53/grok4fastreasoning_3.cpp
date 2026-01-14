#include <bits/stdc++.h>
using namespace std;

void query(const vector<int>& q, int& resp, int n) {
  cout << "?";
  for (int i = 0; i < n; ++i) {
    cout << " " << q[i];
  }
  cout << endl;
  cout.flush();
  cin >> resp;
  if (resp == -1) {
    exit(0);
  }
}

void answer(const vector<int>& p, int n) {
  cout << "!";
  for (int i = 0; i < n; ++i) {
    cout << " " << p[i];
  }
  cout << endl;
  cout.flush();
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int t;
  cin >> t;
  for (int test = 0; test < t; ++test) {
    int n;
    cin >> n;
    int K = n / 2 + 1;
    cout << K << endl;
    cout.flush();
    vector<int> P(n + 1, 0);
    set<int> S;
    for (int i = 1; i <= n; ++i) S.insert(i);
    bool first = true;
    int queries_used = 0;
    while (!S.empty()) {
      int x = *S.begin();
      S.erase(x);
      int v, z;
      if (first) {
        first = false;
        // full scan for first
        vector<int> T;
        for (int i = 1; i <= n; ++i) if (i != x) T.push_back(i);
        sort(T.begin(), T.end());
        int N = T.size();
        vector<int> obs_r(N);
        for (int m = 0; m < N; ++m) {
          vector<int> q(n);
          int ii = 0;
          for (int j = 0; j < m; ++j) q[ii++] = T[j];
          q[ii++] = x;
          for (int j = m; j < N; ++j) q[ii++] = T[j];
          int resp;
          query(q, resp, n);
          obs_r[m] = resp;
          queries_used++;
        }
        // fit
        int best_vp = -1, best_pp = -1;
        int best_c = -1;
        int max_match = 0;
        for (int vp = 0; vp < N; ++vp) {
          for (int pp = 0; pp < N; ++pp) {
            vector<int> delta(N);
            for (int m = 0; m < N; ++m) {
              int cout_ = (pp >= m ? 0 : 1); // 1 if pp > m
              int cin_ = (vp < m ? 1 : 0); // 1 if vp <= m -1 ? wait 0-based
              delta[m] = cout_ + cin_;
            }
            int special_m = K - 1;
            if (special_m >= 0 && special_m < N) {
              delta[special_m] = (vp < special_m ? 1 : 0); // cin only
            }
            int c = obs_r[0] - delta[0];
            bool match = true;
            for (int m = 0; m < N; ++m) {
              if (obs_r[m] - delta[m] != c) {
                match = false;
                break;
              }
            }
            if (match) {
              best_vp = vp;
              best_pp = pp;
              best_c = c;
              max_match++;
            }
          }
        }
        if (max_match == 1) {
          v = T[best_vp];
          z = T[best_pp];
        } else {
          // multiple, assume 2-cycle, pick the first fitting
          v = T[best_vp];
          z = v;
        }
        P[v] = x;
        P[x] = z;
      } else {
        // normal
        v = 1; // stub
        P[v] = x;
        bool two = false; // stub
        if (two) {
          z = v;
          P[x] = z;
        } else {
          z = 1; // stub
          P[x] = z;
        }
      }
      // follow forward
      int curr = x;
      int nxt = z;
      while (P[nxt] == 0 && S.count(nxt)) {
        S.erase(nxt);
        // binary for p(nxt)
        z = 1; // stub
        P[nxt] = z;
        curr = nxt;
        nxt = z;
        queries_used += 7;
      }
    }
    vector<int> pp(n);
    for (int i = 1; i <= n; ++i) pp[i - 1] = P[i];
    answer(pp, n);
  }
  return 0;
}