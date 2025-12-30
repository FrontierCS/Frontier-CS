#include <bits/stdc++.h>
using namespace std;

int N;

int query(int u, int v) {
  cout << "? " << u << " " << v << endl;
  fflush(stdout);
  int d;
  cin >> d;
  return d;
}

void reconstruct(const vector<int>& S, vector<tuple<int, int, int>>& edges) {
  size_t sz = S.size();
  if (sz <= 1) return;
  if (sz == 2) {
    int u = S[0], v = S[1];
    int w = query(u, v);
    edges.emplace_back(u, v, w);
    return;
  }
  int u0 = S[0];
  vector<int> dist_u(N + 1, -1);
  int max_d = -1;
  int far1 = u0;
  for (int v : S) {
    if (v == u0) continue;
    int d = query(u0, v);
    dist_u[v] = d;
    if (d > max_d) {
      max_d = d;
      far1 = v;
    }
  }
  vector<int> dist_f1(N + 1, -1);
  dist_f1[far1] = 0;
  int max_d2 = -1;
  int far2 = far1;
  for (int v : S) {
    if (v == far1) continue;
    int d = query(far1, v);
    dist_f1[v] = d;
    if (d > max_d2) {
      max_d2 = d;
      far2 = v;
    }
  }
  int D = max_d2;
  vector<int> dist_f2(N + 1, -1);
  dist_f2[far2] = 0;
  for (int v : S) {
    if (v == far2) continue;
    int d = query(far2, v);
    dist_f2[v] = d;
  }
  vector<int> path;
  for (int x : S) {
    int dv = dist_f1[x];
    int dw = dist_f2[x];
    if (dv + dw == D) {
      path.push_back(x);
    }
  }
  sort(path.begin(), path.end(), [&](int a, int b) {
    return dist_f1[a] < dist_f1[b];
  });
  for (size_t i = 0; i + 1 < path.size(); ++i) {
    int a = path[i];
    int b = path[i + 1];
    int w = dist_f1[b] - dist_f1[a];
    edges.emplace_back(a, b, w);
  }
  map<long long, int> pos_to_p;
  for (int p : path) {
    pos_to_p[dist_f1[p]] = p;
  }
  vector<vector<int>> subs(path.size());
  for (int x : S) {
    auto it_path = find(path.begin(), path.end(), x);
    if (it_path != path.end()) continue;
    long long dvx = dist_f1[x];
    long long dwx = dist_f2[x];
    long long num = dvx + D - dwx;
    if (num % 2 != 0) continue;
    long long pos = num / 2;
    auto it = pos_to_p.find(pos);
    if (it != pos_to_p.end()) {
      int att = it->second;
      int idx = -1;
      for (int j = 0; j < (int)path.size(); ++j) {
        if (path[j] == att) {
          idx = j;
          break;
        }
      }
      if (idx != -1) {
        subs[idx].push_back(x);
      }
    }
  }
  for (size_t i = 0; i < path.size(); ++i) {
    vector<int> subS;
    subS.push_back(path[i]);
    for (int ss : subs[i]) {
      subS.push_back(ss);
    }
    if (subS.size() > 1) {
      reconstruct(subS, edges);
    }
  }
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int T;
  cin >> T;
  for (int t = 0; t < T; ++t) {
    int n;
    cin >> n;
    N = n;
    vector<int> nodes(n);
    for (int i = 0; i < n; ++i) nodes[i] = i + 1;
    vector<tuple<int, int, int>> edges;
    reconstruct(nodes, edges);
    cout << "!";
    for (auto [u, v, w] : edges) {
      cout << " " << u << " " << v << " " << w;
    }
    cout << endl;
    fflush(stdout);
  }
  return 0;
}