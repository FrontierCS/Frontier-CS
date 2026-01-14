#include <bits/stdc++.h>
using namespace std;

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

vector<pair<int, int>> edges;
int n;

void build_tree(int r, vector<int> U) {
  vector<int> T;
  for (int u : U) if (u != r) T.push_back(u);
  if (T.empty()) return;
  vector<vector<int>> components;
  vector<int> current_T = T;
  while (!current_T.empty()) {
    int ts = current_T.size();
    if (ts == 1) {
      components.push_back({current_T[0]});
      current_T.clear();
      continue;
    }
    if (ts == 2) {
      int a = current_T[0], b = current_T[1];
      cout << 0 << " " << r << " " << a << " " << b << endl;
      cout.flush();
      int m;
      cin >> m;
      if (m == r) {
        components.push_back({a});
        components.push_back({b});
      } else {
        components.push_back({a, b});
      }
      current_T.clear();
      continue;
    }
    // large
    uniform_int_distribution<int> dist(0, ts - 1);
    int idx = dist(rng);
    int p = current_T[idx];
    vector<int> comp = {p};
    for (int j = 0; j < ts; j++) if (j != idx) {
      int other = current_T[j];
      cout << 0 << " " << r << " " << p << " " << other << endl;
      cout.flush();
      int m;
      cin >> m;
      if (m != r) {
        comp.push_back(other);
      }
    }
    components.push_back(comp);
    // remove comp from current_T
    vector<int> newT;
    set<int> comp_set(comp.begin(), comp.end());
    for (int u : current_T) {
      if (comp_set.count(u) == 0) newT.push_back(u);
    }
    current_T = newT;
  }
  // process components
  for (auto comp : components) {
    if (comp.empty()) continue;
    int child;
    if (comp.size() == 1) {
      child = comp[0];
    } else {
      int current = comp[0];
      for (size_t j = 1; j < comp.size(); j++) {
        int next = comp[j];
        cout << 0 << " " << r << " " << current << " " << next << endl;
        cout.flush();
        int m;
        cin >> m;
        current = m;
      }
      child = current;
    }
    int u1 = min(r, child);
    int v1 = max(r, child);
    edges.emplace_back(u1, v1);
    // recurse
    vector<int> subU = comp;
    subU.push_back(child);
    build_tree(child, subU);
  }
}

int main() {
  cin >> n;
  vector<int> U(n);
  for (int i = 0; i < n; i++) U[i] = i + 1;
  build_tree(1, U);
  cout << 1;
  for (auto [u, v] : edges) {
    cout << " " << u << " " << v;
  }
  cout << endl;
  cout.flush();
  return 0;
}