#include <bits/stdc++.h>
using namespace std;

const int H = 12, W = 12;
const int V = (H + 1) * (W + 1);
const int E = (H + 1) * W + H * (W + 1);
const int C = H * W;

int edgeU[E], edgeVtx[E];
int edgeCells[E][2];
int edgeCellCnt[E];
vector<int> vertexEdges[V];
vector<int> cellEdges[C];
int edgeIndexH[H + 1][W];
int edgeIndexV[H][W + 1];

int cellClue[C];
int cellCntOn[C];
int cellCntUnknown[C];

int vDegOn[V];
int vDegUnknown[V];

int edgeState[E]; // -1 unknown, 0 off, 1 on

struct Change {
    int *ptr;
    int prev;
};
vector<Change> changes;

inline void addChange(int &var) {
    changes.push_back({&var, var});
}

inline void undo(int checkpoint) {
    while ((int)changes.size() > checkpoint) {
        *changes.back().ptr = changes.back().prev;
        changes.pop_back();
    }
}

bool setEdge(int eid, int val); // forward

bool updateVertex(int v) {
    if (vDegOn[v] > 2) return false;

    if (vDegOn[v] + vDegUnknown[v] < 2) {
        if (vDegOn[v] == 1) return false;
        if (vDegOn[v] == 0 && vDegUnknown[v] == 1) {
            for (int e : vertexEdges[v]) {
                if (edgeState[e] == -1) {
                    if (!setEdge(e, 0)) return false;
                }
            }
        }
    }

    if (vDegOn[v] == 2) {
        for (int e : vertexEdges[v]) {
            if (edgeState[e] == -1) {
                if (!setEdge(e, 0)) return false;
            }
        }
    } else if (vDegOn[v] == 1 && vDegUnknown[v] == 1) {
        for (int e : vertexEdges[v]) {
            if (edgeState[e] == -1) {
                if (!setEdge(e, 1)) return false;
            }
        }
    }

    if (vDegUnknown[v] == 0 && vDegOn[v] == 1) return false;

    return true;
}

bool updateCell(int cid) {
    int clue = cellClue[cid];
    if (clue < 0) return true;

    if (cellCntOn[cid] > clue) return false;
    if (cellCntOn[cid] + cellCntUnknown[cid] < clue) return false;

    if (cellCntOn[cid] == clue) {
        for (int e : cellEdges[cid]) {
            if (edgeState[e] == -1) {
                if (!setEdge(e, 0)) return false;
            }
        }
    } else if (cellCntOn[cid] + cellCntUnknown[cid] == clue) {
        for (int e : cellEdges[cid]) {
            if (edgeState[e] == -1) {
                if (!setEdge(e, 1)) return false;
            }
        }
    }
    return true;
}

bool setEdge(int eid, int val) {
    if (edgeState[eid] == val) return true;
    if (edgeState[eid] == (val ^ 1)) return false;

    addChange(edgeState[eid]);
    edgeState[eid] = val;

    int u = edgeU[eid];
    int v = edgeVtx[eid];

    if (val == 1) {
        addChange(vDegOn[u]); vDegOn[u]++;
        addChange(vDegUnknown[u]); vDegUnknown[u]--;
        if (!updateVertex(u)) return false;

        addChange(vDegOn[v]); vDegOn[v]++;
        addChange(vDegUnknown[v]); vDegUnknown[v]--;
        if (!updateVertex(v)) return false;
    } else {
        addChange(vDegUnknown[u]); vDegUnknown[u]--;
        if (!updateVertex(u)) return false;

        addChange(vDegUnknown[v]); vDegUnknown[v]--;
        if (!updateVertex(v)) return false;
    }

    for (int k = 0; k < edgeCellCnt[eid]; ++k) {
        int cid = edgeCells[eid][k];
        int clue = cellClue[cid];
        if (clue < 0) continue;
        if (val == 1) {
            addChange(cellCntOn[cid]); cellCntOn[cid]++;
            addChange(cellCntUnknown[cid]); cellCntUnknown[cid]--;
        } else {
            addChange(cellCntUnknown[cid]); cellCntUnknown[cid]--;
        }
        if (!updateCell(cid)) return false;
    }

    return true;
}

bool checkSingleCycle() {
    int totalOnEdges = 0;
    for (int e = 0; e < E; ++e)
        if (edgeState[e] == 1) totalOnEdges++;
    if (totalOnEdges == 0) return false;

    int startV = -1;
    for (int v = 0; v < V; ++v) {
        if (vDegOn[v] > 0) {
            startV = v;
            break;
        }
    }
    if (startV == -1) return false;

    vector<char> visV(V, 0);
    vector<char> visE(E, 0);
    queue<int> q;
    q.push(startV);
    visV[startV] = 1;
    int cntV = 0, cntE = 0;

    while (!q.empty()) {
        int v = q.front(); q.pop();
        cntV++;
        if (vDegOn[v] != 2) return false;
        for (int e : vertexEdges[v]) {
            if (edgeState[e] == 1 && !visE[e]) {
                visE[e] = 1;
                cntE++;
                int u = edgeU[e] ^ edgeVtx[e] ^ v;
                if (!visV[u]) {
                    visV[u] = 1;
                    q.push(u);
                }
            }
        }
    }

    if (cntE != totalOnEdges) return false;

    for (int v = 0; v < V; ++v) {
        if (vDegOn[v] > 0 && !visV[v]) return false;
    }

    return true;
}

int solutionCount;

void dfs() {
    if (solutionCount >= 2) return;

    int bestEdge = -1;
    int bestScore = 1000000000;

    for (int e = 0; e < E; ++e) {
        if (edgeState[e] != -1) continue;
        int score = 1000000000;
        for (int k = 0; k < edgeCellCnt[e]; ++k) {
            int cid = edgeCells[e][k];
            if (cellClue[cid] >= 0) {
                score = min(score, cellCntUnknown[cid]);
            }
        }
        int u = edgeU[e], v = edgeVtx[e];
        score = min(score, vDegUnknown[u]);
        score = min(score, vDegUnknown[v]);
        if (score < bestScore) {
            bestScore = score;
            bestEdge = e;
        }
    }

    if (bestEdge == -1) {
        if (checkSingleCycle()) solutionCount++;
        return;
    }

    int checkpoint = changes.size();
    if (setEdge(bestEdge, 1)) {
        dfs();
    }
    undo(checkpoint);
    if (solutionCount >= 2) return;

    checkpoint = changes.size();
    if (setEdge(bestEdge, 0)) {
        dfs();
    }
    undo(checkpoint);
}

int solvePuzzle(const int clueGrid[H][W]) {
    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j) {
            int cid = i * W + j;
            cellClue[cid] = clueGrid[i][j];
        }

    for (int e = 0; e < E; ++e) edgeState[e] = -1;

    for (int v = 0; v < V; ++v) {
        vDegOn[v] = 0;
        vDegUnknown[v] = (int)vertexEdges[v].size();
    }

    for (int cid = 0; cid < C; ++cid) {
        cellCntOn[cid] = 0;
        if (cellClue[cid] >= 0)
            cellCntUnknown[cid] = 4;
        else
            cellCntUnknown[cid] = 0;
    }

    changes.clear();
    solutionCount = 0;

    dfs();

    if (solutionCount >= 2) return 2;
    return solutionCount;
}

inline int vid(int i, int j) {
    return i * (W + 1) + j;
}

void buildGraph() {
    int eidx = 0;
    for (int i = 0; i <= H; ++i) {
        for (int j = 0; j < W; ++j) {
            int id = eidx++;
            edgeIndexH[i][j] = id;
            int u = vid(i, j);
            int v = vid(i, j + 1);
            edgeU[id] = u;
            edgeVtx[id] = v;
            edgeCellCnt[id] = 0;
            vertexEdges[u].push_back(id);
            vertexEdges[v].push_back(id);
        }
    }
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j <= W; ++j) {
            int id = eidx++;
            edgeIndexV[i][j] = id;
            int u = vid(i, j);
            int v = vid(i + 1, j);
            edgeU[id] = u;
            edgeVtx[id] = v;
            edgeCellCnt[id] = 0;
            vertexEdges[u].push_back(id);
            vertexEdges[v].push_back(id);
        }
    }
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            int cid = i * W + j;
            int e1 = edgeIndexH[i][j];
            int e2 = edgeIndexH[i + 1][j];
            int e3 = edgeIndexV[i][j];
            int e4 = edgeIndexV[i][j + 1];
            cellEdges[cid] = {e1, e2, e3, e4};
            int arr[4] = {e1, e2, e3, e4};
            for (int k = 0; k < 4; ++k) {
                int e = arr[k];
                edgeCells[e][edgeCellCnt[e]++] = cid;
            }
        }
    }
}

bool generateRandomCycle(vector<int> &on, mt19937 &rng) {
    const int maxAttempts = 2000;
    const int maxSteps = 1000;
    const int minLen = 20;

    for (int attempt = 0; attempt < maxAttempts; ++attempt) {
        int start = rng() % V;
        vector<int> path;
        path.reserve(V);
        vector<char> vis(V, 0);
        path.push_back(start);
        vis[start] = 1;

        bool success = false;

        for (int step = 0; step < maxSteps; ++step) {
            int v = path.back();
            int r = v / (W + 1);
            int c = v % (W + 1);
            int dirs[4][2] = {{-1,0},{1,0},{0,-1},{0,1}};
            vector<int> cand;
            cand.reserve(4);
            for (int d = 0; d < 4; ++d) {
                int nr = r + dirs[d][0];
                int nc = c + dirs[d][1];
                if (nr < 0 || nr > H || nc < 0 || nc > W) continue;
                int nv = vid(nr, nc);
                if (!vis[nv] || (nv == start && (int)path.size() >= 4)) {
                    cand.push_back(nv);
                }
            }
            if (cand.empty()) break;
            int nv = cand[rng() % cand.size()];
            if (nv == start && (int)path.size() >= 4) {
                if ((int)path.size() >= minLen) {
                    on.assign(E, 0);
                    for (int i = 0; i + 1 < (int)path.size(); ++i) {
                        int a = path[i], b = path[i + 1];
                        int ra = a / (W + 1), ca = a % (W + 1);
                        int rb = b / (W + 1), cb = b % (W + 1);
                        int eid;
                        if (ra == rb) {
                            int row = ra;
                            int col = min(ca, cb);
                            eid = edgeIndexH[row][col];
                        } else {
                            int row = min(ra, rb);
                            int col = ca;
                            eid = edgeIndexV[row][col];
                        }
                        on[eid] = 1;
                    }
                    int a = path.back(), b = start;
                    int ra = a / (W + 1), ca = a % (W + 1);
                    int rb = b / (W + 1), cb = b % (W + 1);
                    int eid;
                    if (ra == rb) {
                        int row = ra;
                        int col = min(ca, cb);
                        eid = edgeIndexH[row][col];
                    } else {
                        int row = min(ra, rb);
                        int col = ca;
                        eid = edgeIndexV[row][col];
                    }
                    on[eid] = 1;
                    success = true;
                }
                break;
            } else {
                if (!vis[nv]) {
                    vis[nv] = 1;
                    path.push_back(nv);
                } else {
                    break;
                }
            }
        }
        if (success) return true;
    }
    return false;
}

vector<string> generatePuzzle() {
    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
    vector<int> on(E, 0);

    const int MAX_PUZZLE_ATTEMPTS = 60;

    int bestSolCount = -1;
    int bestClue[H][W];

    for (int attempt = 0; attempt < MAX_PUZZLE_ATTEMPTS; ++attempt) {
        bool okCycle = generateRandomCycle(on, rng);
        if (!okCycle) continue;

        int clue[H][W];
        for (int i = 0; i < H; ++i)
            for (int j = 0; j < W; ++j) {
                int cid = i * W + j;
                int cnt = 0;
                for (int e : cellEdges[cid]) {
                    if (on[e]) cnt++;
                }
                if (cnt >= 1 && cnt <= 3)
                    clue[i][j] = cnt;
                else
                    clue[i][j] = -1;
            }

        int sol = solvePuzzle(clue);
        if (sol == 1) {
            vector<string> grid(H, string(W, ' '));
            for (int i = 0; i < H; ++i)
                for (int j = 0; j < W; ++j)
                    if (clue[i][j] >= 1 && clue[i][j] <= 3)
                        grid[i][j] = char('0' + clue[i][j]);
            return grid;
        }

        if (sol > 0 && (bestSolCount == -1 || sol < bestSolCount)) {
            bestSolCount = sol;
            for (int i = 0; i < H; ++i)
                for (int j = 0; j < W; ++j)
                    bestClue[i][j] = clue[i][j];
        }
    }

    // Fallback: use best found (may not be unique, but unlikely to be needed)
    vector<string> grid(H, string(W, ' '));
    if (bestSolCount == -1) {
        // no puzzle found at all, output empty grid (still valid format)
        return grid;
    }
    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            if (bestClue[i][j] >= 1 && bestClue[i][j] <= 3)
                grid[i][j] = char('0' + bestClue[i][j]);
    return grid;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int typeInput;
    if (!(cin >> typeInput)) {
        return 0;
    }

    buildGraph();
    vector<string> puzzle = generatePuzzle();
    for (int i = 0; i < H; ++i) {
        cout << puzzle[i] << '\n';
    }
    return 0;
}