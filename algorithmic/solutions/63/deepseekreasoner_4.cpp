#include <bits/stdc++.h>
using namespace std;

const int MAXN = 10000;
const int MAXM = 15000;
const int Q = 600;
const int K = 30;

int N, M;
vector<pair<int, int>> edges; // store input edges (U_i, V_i)
vector<vector<pair<int, int>>> adj; // original graph adjacency: (neighbor, edge index)
vector<vector<int>> treeAdj; // spanning tree adjacency
bool isTreeEdge[MAXM];
unsigned short distTree[MAXN][MAXN]; // distances in the tree
vector<vector<int>> distQuery; // for each query, distance from root to all nodes
vector<int> roots(Q), answers(Q);

// ---------- spanning tree construction ----------
void buildSpanningTree() {
    vector<bool> visited(N, false);
    queue<int> q;
    visited[0] = true;
    q.push(0);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (auto &e : adj[u]) {
            int v = e.first, idx = e.second;
            if (!visited[v]) {
                visited[v] = true;
                isTreeEdge[idx] = true;
                treeAdj[u].push_back(v);
                treeAdj[v].push_back(u);
                q.push(v);
            }
        }
    }
}

// ---------- BFS to compute distances in tree ----------
void bfsTree(int start, unsigned short dist[]) {
    fill(dist, dist + N, (unsigned short) -1);
    queue<int> q;
    dist[start] = 0;
    q.push(start);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : treeAdj[u]) {
            if (dist[v] == (unsigned short) -1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
}

// ---------- main ----------
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    edges.resize(M);
    adj.resize(N);
    treeAdj.resize(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
    }

    // build spanning tree
    buildSpanningTree();

    // precompute all-pairs distances in the tree
    for (int u = 0; u < N; u++) {
        bfsTree(u, distTree[u]);
    }

    // prepare for queries
    distQuery.assign(Q, vector<int>(N));
    srand(12345); // fixed seed for reproducibility

    for (int q = 0; q < Q; q++) {
        int r = rand() % N;
        roots[q] = r;

        // BFS on tree to compute distances from r
        vector<int> &distR = distQuery[q];
        fill(distR.begin(), distR.end(), -1);
        queue<int> qq;
        distR[r] = 0;
        qq.push(r);
        while (!qq.empty()) {
            int u = qq.front(); qq.pop();
            for (int v : treeAdj[u]) {
                if (distR[v] == -1) {
                    distR[v] = distR[u] + 1;
                    qq.push(v);
                }
            }
        }

        // build orientation
        vector<int> dir(M);
        for (int i = 0; i < M; i++) {
            int u = edges[i].first, v = edges[i].second;
            int tail, head;
            if (isTreeEdge[i]) {
                // tree edge: orient from farther from r to closer
                if (distR[u] < distR[v]) {
                    tail = v; head = u;
                } else {
                    tail = u; head = v;
                }
            } else {
                // non-tree edge: orient from closer to farther, break ties by index
                if (distR[u] < distR[v]) {
                    tail = u; head = v;
                } else if (distR[v] < distR[u]) {
                    tail = v; head = u;
                } else {
                    if (u < v) { tail = u; head = v; }
                    else { tail = v; head = u; }
                }
            }
            // set direction bit: 0 if from U_i to V_i, 1 if from V_i to U_i
            if (tail == u && head == v) dir[i] = 0;
            else dir[i] = 1;
        }

        // output query
        cout << 0;
        for (int i = 0; i < M; i++) cout << ' ' << dir[i];
        cout << endl;
        cout.flush();

        // read answer
        int ans;
        cin >> ans;
        answers[q] = ans;
    }

    // now find A and B
    for (int A = 0; A < N; A++) {
        vector<int> candidates;
        for (int B = 0; B < N; B++) if (B != A) candidates.push_back(B);

        // filter with first K queries
        for (int q = 0; q < K; q++) {
            if (candidates.empty()) break;
            int r = roots[q];
            bool expected = answers[q];
            int distAR = distQuery[q][A];
            vector<int> new_cand;
            for (int B : candidates) {
                int distAB = distTree[A][B];
                int distBR = distQuery[q][B];
                bool onPath = (distAB + distBR == distAR);
                if (onPath == expected) new_cand.push_back(B);
            }
            candidates = new_cand;
        }

        // check remaining queries for each surviving candidate
        for (int B : candidates) {
            bool ok = true;
            for (int q = K; q < Q; q++) {
                int distAR = distQuery[q][A];
                int distAB = distTree[A][B];
                int distBR = distQuery[q][B];
                bool onPath = (distAB + distBR == distAR);
                if (onPath != answers[q]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                cout << "1 " << A << " " << B << endl;
                cout.flush();
                return 0;
            }
        }
    }

    // should never reach here
    return 0;
}