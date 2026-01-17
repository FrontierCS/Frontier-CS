#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
  vector<set<int>> adj(N + 1);
  for (int i = 0; i < M; i++) {
    int a = A[i], b = B[i];
    adj[a].insert(b);
    adj[b].insert(a);
  }
  int root = 1;
  vector<vector<int>> tree(N + 1);
  vector<bool> visited(N + 1, false);
  vector<int> parent(N + 1, -1);
  queue<int> qq;
  qq.push(root);
  visited[root] = true;
  while (!qq.empty()) {
    int u = qq.front();
    qq.pop();
    for (int v : adj[u]) {
      if (!visited[v]) {
        visited[v] = true;
        parent[v] = u;
        tree[u].push_back(v);
        qq.push(v);
      }
    }
  }
  vector<int> sub_height(N + 1), sub_width(N + 1);
  function<void(int, int)> comp_size = [&](int u, int p) {
    int numc = tree[u].size();
    int maxch = 0;
    int sumcw = 0;
    int nsep = max(0, numc - 1);
    for (int v : tree[u]) {
      comp_size(v, u);
      maxch = max(maxch, sub_height[v]);
      sumcw += sub_width[v];
    }
    int hchild = (numc == 0 ? 0 : maxch);
    sub_height[u] = 3 + hchild;
    int wchild = (numc == 0 ? 0 : sumcw + nsep);
    int deg = adj[u].size();
    int wblock = (deg == 0 ? 1 : 3 * deg);
    sub_width[u] = max(wblock, wchild);
  };
  comp_size(root, -1);
  int toth = sub_height[root];
  int totw = sub_width[root];
  int K = max(toth, totw);
  vector<vector<int>> C(K, vector<int>(K, 0));
  function<void(int, int, int)> do_place = [&](int u, int r0, int c0) {
    int sw = sub_width[u];
    int deg = adj[u].size();
    int wb = (deg == 0 ? 1 : 3 * deg);
    for (int i = 0; i < 3; i++) {
      int rr = r0 + i;
      if (rr >= K) continue;
      for (int j = 0; j < sw; j++) {
        int cc = c0 + j;
        if (cc >= K) break;
        C[rr][cc] = u;
      }
    }
    vector<int> neigh(adj[u].begin(), adj[u].end());
    int d = neigh.size();
    int pstart = c0;
    for (int k = 0; k < d; k++) {
      int v = neigh[k];
      int pc = pstart + 3 * k + 1;
      if (pc < c0 + sw && pc < K) {
        int rr = r0 + 1;
        if (rr < K) C[rr][pc] = v;
      }
    }
    auto& children = tree[u];
    int numc = children.size();
    if (numc == 0) return;
    int r1 = r0 + 3;
    if (r1 >= K) return;
    int maxch = 0;
    for (int v : children) maxch = max(maxch, sub_height[v]);
    vector<int> ch_starts(numc);
    int this_c = c0;
    int wchild_actual = 0;
    for (int i = 0; i < numc; i++) {
      int v = children[i];
      ch_starts[i] = this_c;
      do_place(v, r1, this_c);
      this_c += sub_width[v];
      wchild_actual += sub_width[v];
      if (i < numc - 1) {
        int sep_c = this_c;
        for (int rr = r1; rr < r1 + maxch && rr < K; rr++) {
          if (sep_c < K) C[rr][sep_c] = u;
        }
        this_c++;
        wchild_actual++;
      }
    }
    for (int i = 0; i < numc; i++) {
      int v = children[i];
      int startc = ch_starts[i];
      int endc = startc + sub_width[v] - 1;
      int child_h = sub_height[v];
      int gap_start_r = r1 + child_h;
      for (int rr = gap_start_r; rr < r1 + maxch && rr < K; rr++) {
        for (int cc = startc; cc <= endc && cc < K; cc++) {
          C[rr][cc] = v;
        }
      }
    }
    int children_end_c = c0 + wchild_actual;
    for (int rr = r1; rr < r1 + maxch && rr < K; rr++) {
      for (int cc = children_end_c; cc < c0 + sw && cc < K; cc++) {
        C[rr][cc] = u;
      }
    }
  };
  do_place(root, 0, 0, C);
  if (toth < K) {
    for (int r = toth; r < K; r++) {
      for (int j = 0; j < K; j++) {
        C[r][j] = C[toth - 1][j];
      }
    }
  }
  if (totw < K) {
    for (int j = totw; j < K; j++) {
      for (int i = 0; i < K; i++) {
        C[i][j] = C[i][totw - 1];
      }
    }
  }
  return C;
}

int main() {
  int T;
  cin >> T;
  for (int t = 0; t < T; t++) {
    int N, M;
    cin >> N >> M;
    vector<int> AA(M), BB(M);
    for (int i = 0; i < M; i++) {
      cin >> AA[i] >> BB[i];
    }
    auto cmap = create_map(N, M, AA, BB);
    int KK = cmap.size();
    cout << KK << endl;
    for (int q = 0; q < KK; q++) {
      if (q > 0) cout << " ";
      cout << KK;
    }
    cout << endl;
    cout << endl;
    for (int i = 0; i < KK; i++) {
      for (int j = 0; j < KK; j++) {
        if (j > 0) cout << " ";
        cout << cmap[i][j];
      }
      cout << endl;
    }
  }
  return 0;
}