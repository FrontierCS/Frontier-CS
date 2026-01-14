#include <bits/stdc++.h>

using namespace std;

int N;
vector<pair<int, int>> edges;

void discover(vector<int> V) {
  int m = V.size();
  if (m <= 1) return;
  if (m == 2) {
    int u = V[0], v = V[1];
    edges.emplace_back(min(u, v), max(u, v));
    return;
  }
  int a = V[0];
  int b = V[1];
  // find proj and S
  vector<int> proj(N+1, 0);
  set<int> S_set;
  proj[a] = a;
  proj[b] = b;
  S_set.insert(a);
  S_set.insert(b);
  for (int i = 2; i < m; ++i) {
    int x = V[i];
    cout << 0 << " " << a << " " << b << " " << x << endl;
    cout.flush();
    int p;
    cin >> p;
    proj[x] = p;
    if (p == x) S_set.insert(x);
  }
  vector<int> S(S_set.begin(), S_set.end());
  int s = S.size();
  if (s == 2) {
    edges.emplace_back(a, b);
    map<int, vector<int>> groups;
    for (int x : V) {
      groups[proj[x]].push_back(x);
    }
    for (auto& p : groups) {
      if (p.second.size() > 1) {
        sort(p.second.begin(), p.second.end());
        discover(p.second);
      }
    }
    return;
  }
  // order the path
  vector<int> to_sort;
  for (int p : S) if (p != a) to_sort.push_back(p);
  // comparator
  auto comp = [&](int p, int q) -> bool {
    cout << 0 << " " << a << " " << p << " " << q << endl;
    cout.flush();
    int closer;
    cin >> closer;
    return closer == p;
  };
  sort(to_sort.begin(), to_sort.end(), comp);
  // now path
  vector<int> path = {a};
  path.insert(path.end(), to_sort.begin(), to_sort.end());
  // add path edges
  for (int i = 0; i < s - 1; ++i) {
    edges.emplace_back(path[i], path[i + 1]);
  }
  // groups
  map<int, vector<int>> groups;
  for (int x : V) {
    int j = proj[x];
    groups[j].push_back(x);
  }
  // recurse
  for (int j : S) {
    vector<int>& g = groups[j];
    if (g.size() > 1) {
      sort(g.begin(), g.end());
      discover(g);
    }
  }
}

int main() {
  cin >> N;
  vector<int> all(N);
  for (int i = 0; i < N; ++i) all[i] = i + 1;
  discover(all);
  // now output
  cout << 1;
  for (auto [u, v] : edges) {
    cout << " " << u << " " << v;
  }
  cout << endl;
  cout.flush();
  return 0;
}