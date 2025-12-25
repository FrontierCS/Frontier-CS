#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  srand(time(0));
  int t;
  cin >> t;
  for (int test = 0; test < t; ++test) {
    int n;
    cin >> n;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
      int u, v;
      cin >> u >> v;
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
    vector<int> f(n + 1, 0);
    for (int u = 1; u <= n; ++u) {
      cout << "? 1 1 " << u << endl;
      cout.flush();
      cin >> f[u];
    }
    // Find candidates
    vector<int> candidates;
    vector<vector<int>> candidate_parents; // for each candidate, its parent array
    for (int r = 1; r <= n; ++r) {
      if (abs(f[r]) != 1) continue;
      vector<int> parent(n + 1, -1);
      vector<bool> visited(n + 1, false);
      queue<int> q;
      q.push(r);
      visited[r] = true;
      parent[r] = 0;
      bool valid = true;
      int visited_count = 1;
      while (!q.empty() && valid) {
        int p = q.front();
        q.pop();
        for (int child : adj[p]) {
          if (!visited[child]) {
            visited[child] = true;
            parent[child] = p;
            if (abs(f[child] - f[p]) != 1) {
              valid = false;
              break;
            }
            q.push(child);
            ++visited_count;
          }
        }
      }
      if (valid && visited_count == n) {
        candidates.push_back(r);
        candidate_parents.push_back(parent);
      }
    }
    int kk = candidates.size();
    if (kk == 0) {
      // impossible, but skip or error
      continue;
    } else if (kk == 1) {
      int r = candidates[0];
      vector<int> parent = candidate_parents[0];
      vector<int> val(n + 1);
      val[r] = f[r];
      for (int u = 1; u <= n; ++u) {
        if (u == r) continue;
        int p = parent[u];
        val[u] = f[u] - f[p];
      }
      cout << "!";
      for (int i = 1; i <= n; ++i) {
        cout << " " << val[i];
      }
      cout << endl;
      cout.flush();
      continue;
    }
    // kk > 1, disambiguate
    bool found = false;
    int chosen_y = -1;
    vector<int> chosen_T;
    vector<bitset<1001>> saved_subts;
    vector<int> saved_delta;
    bitset<1001> saved_T;
    for (int yi = 0; yi < kk; ++yi) {
      int y = candidates[yi];
      vector<bitset<1001>> subts(kk);
      vector<int> delta(kk);
      bool can = true;
      for (int ci = 0; ci < kk; ++ci) {
        int rc = candidates[ci];
        // build parent for rc
        vector<int> parent(n + 1, -1);
        vector<bool> vis(n + 1, false);
        queue<int> qq;
        qq.push(rc);
        vis[rc] = true;
        parent[rc] = 0;
        while (!qq.empty()) {
          int pp = qq.front();
          qq.pop();
          for (int ch : adj[pp]) {
            if (!vis[ch]) {
              vis[ch] = true;
              parent[ch] = pp;
              qq.push(ch);
            }
          }
        }
        // compute val_y
        int val_y;
        if (y == rc) {
          val_y = f[y];
        } else {
          int py = parent[y];
          val_y = f[y] - f[py];
        }
        delta[ci] = -2 * val_y;
        // build children
        vector<vector<int>> children(n + 1);
        for (int u = 1; u <= n; ++u) {
          if (parent[u] != 0) {
            children[parent[u]].push_back(u);
          }
        }
        // collect subtree of y
        vector<bool> in_subt(n + 1, false);
        queue<int> qsub;
        qsub.push(y);
        in_subt[y] = true;
        while (!qsub.empty()) {
          int pp = qsub.front();
          qsub.pop();
          for (int ch : children[pp]) {
            if (!in_subt[ch]) {
              in_subt[ch] = true;
              qsub.push(ch);
            }
          }
        }
        // set bitset
        bitset<1001>& bsc = subts[ci];
        bsc.reset();
        for (int u = 1; u <= n; ++u) {
          if (in_subt[u]) bsc.set(u);
        }
      }
      // now try random T
      int max_tries = 100;
      bool this_y_works = false;
      bitset<1001> best_bsT;
      for (int tryy = 0; tryy < max_tries; ++tryy) {
        bitset<1001> bsT;
        bsT.reset();
        for (int v = 1; v <= n; ++v) {
          if (rand() % 2) bsT.set(v);
        }
        vector<int> offsets(kk);
        set<int> uniq;
        bool distinct = true;
        for (int ci = 0; ci < kk; ++ci) {
          size_t sc = (subts[ci] & bsT).count();
          offsets[ci] = delta[ci] * (int)sc;
          if (uniq.count(offsets[ci])) {
            distinct = false;
            break;
          }
          uniq.insert(offsets[ci]);
        }
        if (distinct) {
          this_y_works = true;
          best_bsT = bsT;
          break;
        }
      }
      if (this_y_works) {
        found = true;
        chosen_y = y;
        saved_subts = subts;
        saved_delta = delta;
        saved_T = best_bsT;
        chosen_T.clear();
        for (int v = 1; v <= n; ++v) {
          if (saved_T[v]) chosen_T.push_back(v);
        }
        break;
      }
    }
    if (!found) {
      // fallback, pick first
      int r = candidates[0];
      vector<int> parent = candidate_parents[0];
      vector<int> val(n + 1);
      val[r] = f[r];
      for (int u = 1; u <= n; ++u) {
        if (u == r) continue;
        int p = parent[u];
        val[u] = f[u] - f[p];
      }
      cout << "!";
      for (int i = 1; i <= n; ++i) {
        cout << " " << val[i];
      }
      cout << endl;
      cout.flush();
      continue;
    }
    // now perform the queries
    cout << "? 2 " << chosen_y << endl;
    cout.flush();
    // query sum
    int kt = chosen_T.size();
    cout << "? 1 " << kt;
    for (int u : chosen_T) {
      cout << " " << u;
    }
    cout << endl;
    cout.flush();
    int s;
    cin >> s;
    long long G0 = 0;
    for (int i = 1; i <= n; ++i) G0 += f[i];
    long long actual_offset = (long long)s - G0;
    // find true_ci
    int true_ci = -1;
    for (int ci = 0; ci < kk; ++ci) {
      size_t sc = (saved_subts[ci] & saved_T).count();
      int pred = saved_delta[ci] * (int)sc;
      if ((long long)pred == actual_offset) {
        true_ci = ci;
        break;
      }
    }
    if (true_ci == -1) {
      // error, fallback
      true_ci = 0;
    }
    int r = candidates[true_ci];
    // compute parent for r
    vector<int> parent(n + 1, -1);
    vector<bool> visited(n + 1, false);
    queue<int> q;
    q.push(r);
    visited[r] = true;
    parent[r] = 0;
    while (!q.empty()) {
      int p = q.front();
      q.pop();
      for (int child : adj[p]) {
        if (!visited[child]) {
          visited[child] = true;
          parent[child] = p;
          q.push(child);
        }
      }
    }
    // compute val
    vector<int> val(n + 1);
    val[r] = f[r];
    for (int u = 1; u <= n; ++u) {
      if (u == r) continue;
      int p = parent[u];
      val[u] = f[u] - f[p];
    }
    // flip chosen_y
    val[chosen_y] = -val[chosen_y];
    // output
    cout << "!";
    for (int i = 1; i <= n; ++i) {
      cout << " " << val[i];
    }
    cout << endl;
    cout.flush();
  }
  return 0;
}