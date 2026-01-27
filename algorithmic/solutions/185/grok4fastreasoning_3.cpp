#include <bits/stdc++.h>
using namespace std;

int main() {
  srand(time(NULL));
  int N, M;
  cin >> N >> M;
  const int MAXN = 1005;
  bitset<MAXN> adj[MAXN];
  for(int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    u--; v--;
    if(u != v) {
      adj[u][v] = 1;
      adj[v][u] = 1;
    }
  }
  vector<int> best_clique;
  int best_size = 0;
  const int TRIES = 30;
  for(int trial = 0; trial < TRIES; trial++) {
    vector<int> scan_order(N);
    iota(scan_order.begin(), scan_order.end(), 0);
    random_shuffle(scan_order.begin(), scan_order.end());
    vector<int> clique;
    bitset<MAXN> candidates;
    candidates.reset();
    for(int i = 0; i < N; i++) candidates.set(i);
    while(candidates.any()) {
      int maxdeg = -1;
      int best = -1;
      for(int j = 0; j < N; j++) {
        int i = scan_order[j];
        if(!candidates[i]) continue;
        bitset<MAXN> inter = adj[i] & candidates;
        int d = inter.count();
        if(d > maxdeg) {
          maxdeg = d;
          best = i;
        }
      }
      if(best == -1) break;
      clique.push_back(best);
      candidates = adj[best] & candidates;
    }
    if((int)clique.size() > best_size) {
      best_size = clique.size();
      best_clique = clique;
    }
  }
  vector<int> selected(N, 0);
  for(int v : best_clique) {
    selected[v] = 1;
  }
  for(int i = 0; i < N; i++) {
    cout << selected[i] << '\n';
  }
  return 0;
}