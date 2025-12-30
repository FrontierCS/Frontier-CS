#include <bits/stdc++.h>
using namespace std;

int N, si, sj;
vector<string> grid;

int R;
vector<int> node_i, node_j, node_w;
vector<vector<int>> treeAdj;
string route;

void addMove(int from, int to) {
    int i1 = node_i[from], j1 = node_j[from];
    int i2 = node_i[to], j2 = node_j[to];
    char ch;
    if (i2 == i1 - 1 && j2 == j1) ch = 'U';
    else if (i2 == i1 + 1 && j2 == j1) ch = 'D';
    else if (i2 == i1 && j2 == j1 - 1) ch = 'L';
    else if (i2 == i1 && j2 == j1 + 1) ch = 'R';
    else return;  // Should not happen
    route.push_back(ch);
}

void dfs(int u, int parent) {
    for (int v : treeAdj[u]) {
        if (v == parent) continue;
        addMove(u, v);
        dfs(v, u);
        addMove(v, u);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> si >> sj)) return 0;
    grid.assign(N, "");
    for (int i = 0; i < N; i++) cin >> grid[i];

    vector<vector<int>> id(N, vector<int>(N, -1));
    node_i.clear();
    node_j.clear();
    node_w.clear();
    R = 0;

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (grid[i][j] != '#') {
                id[i][j] = R++;
                node_i.push_back(i);
                node_j.push_back(j);
                node_w.push_back(grid[i][j] - '0');
            }
        }
    }

    vector<vector<int>> adj(R);
    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (id[i][j] == -1) continue;
            int u = id[i][j];
            for (int k = 0; k < 4; k++) {
                int ni = i + di[k];
                int nj = j + dj[k];
                if (0 <= ni && ni < N && 0 <= nj && nj < N && id[ni][nj] != -1) {
                    int v = id[ni][nj];
                    adj[u].push_back(v);
                }
            }
        }
    }

    int root = id[si][sj];

    vector<int> parent(R, -1);
    vector<int> bestCost(R, INT_MAX);
    vector<char> used(R, 0);
    using P = pair<int, int>;
    priority_queue<P, vector<P>, greater<P>> pq;

    bestCost[root] = 0;
    pq.push({0, root});
    int cnt = 0;

    while (!pq.empty() && cnt < R) {
        P top = pq.top(); pq.pop();
        int c = top.first, u = top.second;
        if (used[u]) continue;
        used[u] = 1;
        cnt++;
        for (int v : adj[u]) {
            if (used[v]) continue;
            int cost = node_w[u] + node_w[v];
            if (cost < bestCost[v]) {
                bestCost[v] = cost;
                parent[v] = u;
                pq.push({cost, v});
            }
        }
    }

    treeAdj.assign(R, vector<int>());
    for (int v = 0; v < R; v++) {
        int p = parent[v];
        if (p >= 0) {
            treeAdj[v].push_back(p);
            treeAdj[p].push_back(v);
        }
    }

    route.clear();
    route.reserve(max(1, 2 * R));

    dfs(root, -1);

    cout << route << '\n';
    return 0;
}