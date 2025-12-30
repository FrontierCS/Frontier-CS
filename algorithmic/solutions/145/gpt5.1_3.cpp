#include <bits/stdc++.h>
using namespace std;

const int H = 12, W = 12;
const int VH = H + 1, VW = W + 1;
const int NUM_VERT = VH * VW;          // 13 * 13 = 169
const int NUM_H_EDGES = VH * W;        // 13 * 12 = 156
const int NUM_V_EDGES = H * VW;        // 12 * 13 = 156
const int NUM_EDGE = NUM_H_EDGES + NUM_V_EDGES; // 312
const int NUM_CELL = H * W;            // 144

struct EdgeInfo {
    int v1, v2;
    int cells[2];
    unsigned char cellCnt;
};

int edgeIndexH[VH][W];
int edgeIndexV[H][VW];

EdgeInfo edges[NUM_EDGE];
vector<int> vertexEdges[NUM_VERT];
vector<int> cellEdges[NUM_CELL];
int degTotal[NUM_VERT];
vector<int> neighbors[NUM_VERT];

mt19937 rng(123456);

// Solver state
signed char edgeState[NUM_EDGE];          // -1 unknown, 0 off, 1 on
unsigned char cellOn[NUM_CELL];
unsigned char cellUnk[NUM_CELL];
unsigned char degOn[NUM_VERT];
unsigned char degUnk[NUM_VERT];
int digitsCell[NUM_CELL];                 // -1 blank, 0..3

int solutionCount;
int solutionLimit = 2;

struct Snapshot {
    signed char edgeState[NUM_EDGE];
    unsigned char cellOn[NUM_CELL];
    unsigned char cellUnk[NUM_CELL];
    unsigned char degOn[NUM_VERT];
    unsigned char degUnk[NUM_VERT];
};

inline void captureState(Snapshot &s) {
    memcpy(s.edgeState, edgeState, sizeof(edgeState));
    memcpy(s.cellOn, cellOn, sizeof(cellOn));
    memcpy(s.cellUnk, cellUnk, sizeof(cellUnk));
    memcpy(s.degOn, degOn, sizeof(degOn));
    memcpy(s.degUnk, degUnk, sizeof(degUnk));
}

inline void restoreState(const Snapshot &s) {
    memcpy(edgeState, s.edgeState, sizeof(edgeState));
    memcpy(cellOn, s.cellOn, sizeof(cellOn));
    memcpy(cellUnk, s.cellUnk, sizeof(cellUnk));
    memcpy(degOn, s.degOn, sizeof(degOn));
    memcpy(degUnk, s.degUnk, sizeof(degUnk));
}

inline bool setEdge(int e, int val) {
    if (edgeState[e] == val) return true;
    if (edgeState[e] != -1 && edgeState[e] != val) return false;
    edgeState[e] = (signed char)val;

    EdgeInfo &E = edges[e];
    for (int i = 0; i < E.cellCnt; ++i) {
        int cid = E.cells[i];
        if (val == 1) cellOn[cid]++;
        cellUnk[cid]--;
    }

    int v1 = E.v1, v2 = E.v2;
    if (val == 1) {
        degOn[v1]++; degUnk[v1]--;
        degOn[v2]++; degUnk[v2]--;
    } else { // OFF
        degUnk[v1]--; degUnk[v2]--;
    }
    return true;
}

bool propagate() {
    while (true) {
        bool changed = false;

        // Cell constraints
        for (int cid = 0; cid < NUM_CELL; ++cid) {
            int d = digitsCell[cid];
            if (d == -1) continue;
            int on = cellOn[cid];
            int unk = cellUnk[cid];
            if (on > d || on + unk < d) return false;
            if (unk == 0) continue;

            if (on == d) {
                // remaining edges must be OFF
                for (int e : cellEdges[cid]) {
                    if (edgeState[e] == -1) {
                        if (!setEdge(e, 0)) return false;
                        changed = true;
                    }
                }
            } else if (on + unk == d) {
                // remaining edges must be ON
                for (int e : cellEdges[cid]) {
                    if (edgeState[e] == -1) {
                        if (!setEdge(e, 1)) return false;
                        changed = true;
                    }
                }
            }
        }

        // Vertex constraints
        for (int v = 0; v < NUM_VERT; ++v) {
            int on = degOn[v];
            int unk = degUnk[v];
            if (on > 2) return false;
            if (unk == 0) {
                if (on != 0 && on != 2) return false;
                continue;
            }
            if (on == 2) {
                // remaining edges must be OFF
                for (int e : vertexEdges[v]) {
                    if (edgeState[e] == -1) {
                        if (!setEdge(e, 0)) return false;
                        changed = true;
                    }
                }
            } else if (on == 0 && unk == 1) {
                // last edge must be OFF (can't have degree 1)
                for (int e : vertexEdges[v]) {
                    if (edgeState[e] == -1) {
                        if (!setEdge(e, 0)) return false;
                        changed = true;
                        break;
                    }
                }
            } else if (on >= 1 && on + unk == 2) {
                // must finish with degree 2 -> all unknown ON
                for (int e : vertexEdges[v]) {
                    if (edgeState[e] == -1) {
                        if (!setEdge(e, 1)) return false;
                        changed = true;
                    }
                }
            }
        }

        if (!changed) break;
    }
    return true;
}

int pickEdge() {
    int best = -1;
    int bestScore = INT_MAX;
    for (int e = 0; e < NUM_EDGE; ++e) {
        if (edgeState[e] != -1) continue;
        int score = 0;
        EdgeInfo &E = edges[e];
        for (int i = 0; i < E.cellCnt; ++i) {
            int cid = E.cells[i];
            if (digitsCell[cid] >= 0) score += cellUnk[cid];
        }
        score += degUnk[E.v1] + degUnk[E.v2];
        if (score < bestScore) {
            bestScore = score;
            best = e;
        }
    }
    return best;
}

bool checkSingleCycle() {
    int start = -1;
    for (int v = 0; v < NUM_VERT; ++v) {
        int on = degOn[v];
        if (on != 0 && on != 2) return false;
        if (on > 0 && start == -1) start = v;
    }
    if (start == -1) return false; // no edges

    vector<char> visV(NUM_VERT, 0);
    vector<char> visE(NUM_EDGE, 0);
    stack<int> st;
    st.push(start);
    visV[start] = 1;
    while (!st.empty()) {
        int v = st.top(); st.pop();
        for (int e : vertexEdges[v]) {
            if (edgeState[e] == 1 && !visE[e]) {
                visE[e] = 1;
                int w = edges[e].v1 ^ edges[e].v2 ^ v;
                if (!visV[w]) {
                    visV[w] = 1;
                    st.push(w);
                }
            }
        }
    }

    for (int e = 0; e < NUM_EDGE; ++e) {
        if (edgeState[e] == 1 && !visE[e]) return false;
    }
    for (int v = 0; v < NUM_VERT; ++v) {
        if (degOn[v] > 0 && !visV[v]) return false;
    }
    return true;
}

void dfs() {
    if (solutionCount >= solutionLimit) return;
    if (!propagate()) return;

    int e = pickEdge();
    if (e == -1) {
        if (checkSingleCycle()) solutionCount++;
        return;
    }

    Snapshot backup;

    // Try ON first
    captureState(backup);
    if (setEdge(e, 1)) {
        dfs();
    }
    restoreState(backup);

    if (solutionCount >= solutionLimit) return;

    // Then OFF
    captureState(backup);
    if (setEdge(e, 0)) {
        dfs();
    }
    restoreState(backup);
}

int countSolutions(const vector<string> &grid) {
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int cid = r * W + c;
            char ch = grid[r][c];
            if (ch >= '0' && ch <= '3') digitsCell[cid] = ch - '0';
            else digitsCell[cid] = -1;
        }
    }

    for (int e = 0; e < NUM_EDGE; ++e) edgeState[e] = -1;
    for (int cid = 0; cid < NUM_CELL; ++cid) {
        cellOn[cid] = 0;
        cellUnk[cid] = 4;
    }
    for (int v = 0; v < NUM_VERT; ++v) {
        degOn[v] = 0;
        degUnk[v] = degTotal[v];
    }

    solutionCount = 0;
    dfs();
    return solutionCount;
}

// Graph construction helpers
inline int edgeIdFromVertices(int a, int b) {
    if (a > b) swap(a, b);
    int r1 = a / VW, c1 = a % VW;
    int r2 = b / VW, c2 = b % VW;
    if (r1 == r2) {
        // horizontal
        int r = r1, c = c1;
        return edgeIndexH[r][c];
    } else {
        // vertical
        int r = r1, c = c1;
        return edgeIndexV[r][c];
    }
}

void buildGraph() {
    int eid = 0;

    // Horizontal edges
    for (int r = 0; r < VH; ++r) {
        for (int c = 0; c < W; ++c) {
            int v1 = r * VW + c;
            int v2 = r * VW + (c + 1);
            edgeIndexH[r][c] = eid;
            edges[eid].v1 = v1;
            edges[eid].v2 = v2;
            edges[eid].cellCnt = 0;
            vertexEdges[v1].push_back(eid);
            vertexEdges[v2].push_back(eid);
            neighbors[v1].push_back(v2);
            neighbors[v2].push_back(v1);
            ++eid;
        }
    }

    // Vertical edges
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < VW; ++c) {
            int v1 = r * VW + c;
            int v2 = (r + 1) * VW + c;
            edgeIndexV[r][c] = eid;
            edges[eid].v1 = v1;
            edges[eid].v2 = v2;
            edges[eid].cellCnt = 0;
            vertexEdges[v1].push_back(eid);
            vertexEdges[v2].push_back(eid);
            neighbors[v1].push_back(v2);
            neighbors[v2].push_back(v1);
            ++eid;
        }
    }

    // Cells and their edges
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int cid = r * W + c;
            cellEdges[cid].clear();
            int eTop = edgeIndexH[r][c];
            int eBottom = edgeIndexH[r + 1][c];
            int eLeft = edgeIndexV[r][c];
            int eRight = edgeIndexV[r][c + 1];
            int arr[4] = {eTop, eRight, eBottom, eLeft};
            for (int k = 0; k < 4; ++k) {
                int e = arr[k];
                cellEdges[cid].push_back(e);
                EdgeInfo &E = edges[e];
                E.cells[E.cellCnt++] = cid;
            }
        }
    }

    for (int v = 0; v < NUM_VERT; ++v) {
        degTotal[v] = (int)vertexEdges[v].size();
    }
}

void generateRandomCycle(vector<int> &cycle) {
    vector<int> parent(NUM_VERT, -1);
    vector<int> st;
    st.push_back(0);
    parent[0] = -2; // sentinel for root

    while (!st.empty()) {
        int v = st.back(); st.pop_back();
        auto nb = neighbors[v];
        shuffle(nb.begin(), nb.end(), rng);
        for (int u : nb) {
            if (parent[u] == -1) {
                parent[u] = v;
                st.push_back(u);
            }
        }
    }

    vector<char> inTree(NUM_EDGE, 0);
    for (int u = 0; u < NUM_VERT; ++u) {
        int p = parent[u];
        if (p >= 0) {
            int eid = edgeIdFromVertices(u, p);
            inTree[eid] = 1;
        }
    }

    vector<int> nonTree;
    nonTree.reserve(NUM_EDGE);
    for (int e = 0; e < NUM_EDGE; ++e) {
        if (!inTree[e]) nonTree.push_back(e);
    }

    int eExtra = nonTree[rng() % nonTree.size()];
    int a = edges[eExtra].v1;
    int b = edges[eExtra].v2;

    vector<char> mark(NUM_VERT, 0);
    int x = a;
    while (x != -2) {
        mark[x] = 1;
        x = parent[x];
    }

    int y = b;
    while (!mark[y]) {
        y = parent[y];
    }
    int lca = y;

    vector<int> path1, path2;
    x = a;
    while (x != lca) {
        int p = parent[x];
        int eid = edgeIdFromVertices(x, p);
        path1.push_back(eid);
        x = p;
    }
    y = b;
    while (y != lca) {
        int p = parent[y];
        int eid = edgeIdFromVertices(y, p);
        path2.push_back(eid);
        y = p;
    }
    reverse(path2.begin(), path2.end());

    cycle.clear();
    cycle.reserve(path1.size() + path2.size() + 1);
    for (int e : path1) cycle.push_back(e);
    for (int e : path2) cycle.push_back(e);
    cycle.push_back(eExtra);
}

vector<string> makeGridFromCycle(const vector<int> &cycle, int type) {
    vector<int> inLoop(NUM_EDGE, 0);
    for (int e : cycle) inLoop[e] = 1;

    vector<string> grid(H, string(W, ' '));
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int eTop = edgeIndexH[r][c];
            int eBottom = edgeIndexH[r + 1][c];
            int eLeft = edgeIndexV[r][c];
            int eRight = edgeIndexV[r][c + 1];
            int cnt = inLoop[eTop] + inLoop[eBottom] + inLoop[eLeft] + inLoop[eRight];
            char ch = ' ';
            if (type == 0) {
                if (cnt <= 3) ch = char('0' + cnt);
            } else { // type == 1
                if (cnt >= 1 && cnt <= 3) ch = char('0' + cnt);
            }
            grid[r][c] = ch;
        }
    }
    return grid;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    buildGraph();

    int t;
    if (!(cin >> t)) return 0;

    const int MAX_ATTEMPTS = 5;
    vector<string> bestGrid(H, string(W, ' '));
    bool found = false;
    vector<int> cycle;

    for (int attempt = 0; attempt < MAX_ATTEMPTS; ++attempt) {
        generateRandomCycle(cycle);
        vector<string> grid = makeGridFromCycle(cycle, t);
        int cnt = countSolutions(grid);
        if (attempt == 0) bestGrid = grid;
        if (cnt == 1) {
            bestGrid = grid;
            found = true;
            break;
        }
    }

    // If not found, fall back to first attempt (should be extremely unlikely to fail uniqueness)
    for (int r = 0; r < H; ++r) {
        cout << bestGrid[r] << '\n';
    }

    return 0;
}