#include <bits/stdc++.h>
using namespace std;

int main() {
  int t;
  cin >> t;
  for (int test = 0; test < t; test++) {
    int n, m, startv, base;
    cin >> n >> m >> startv >> base;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
      int u, v;
      cin >> u >> v;
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
    // first view
    int d;
    cin >> d;
    vector<int> ndeg(d), nflag(d);
    for (int j = 0; j < d; j++) {
      cin >> ndeg[j] >> nflag[j];
    }
    while (true) {
      // decide chosen: prefer unvisited with max deg, else visited with max deg
      int chosen = -1;
      int max_type = -1;
      bool found_unvisited = false;
      for (int j = 0; j < d; j++) {
        if (nflag[j] == 0 && ndeg[j] > max_type) {
          max_type = ndeg[j];
          chosen = j + 1;
          found_unvisited = true;
        }
      }
      if (!found_unvisited) {
        max_type = -1;
        for (int j = 0; j < d; j++) {
          if (nflag[j] == 1 && ndeg[j] > max_type) {
            max_type = ndeg[j];
            chosen = j + 1;
          }
        }
        if (chosen == -1) chosen = 1; // fallback
      }
      cout << chosen << endl;
      cout.flush();
      // read response
      string response;
      cin >> response;
      if (response == "AC" || response == "F") {
        break;
      }
      // else it's d
      d = stoi(response);
      ndeg.resize(d);
      nflag.resize(d);
      for (int j = 0; j < d; j++) {
        cin >> ndeg[j] >> nflag[j];
      }
    }
  }
  return 0;
}