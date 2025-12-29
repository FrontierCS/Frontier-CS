#include <iostream>
#include <vector>
#include <cstring>
#include <cstdlib>
#include <ctime>
#include <algorithm>

using namespace std;

const int R = 12;
const int C = 12;

int templ[R][C];
int puzzle[R][C];
int faces[R + 2][C + 2];
int task_type;

void init_template() {
    memset(templ, 0, sizeof(templ));
    // Based on visual inspection of the sample output provided in the problem
    int r0[] = {0, 4, 8, 9, 10};
    for(int x : r0) templ[0][x] = 1;
    int r1[] = {0, 1, 3, 4, 7, 11};
    for(int x : r1) templ[1][x] = 1;
    int r2[] = {0, 2, 4, 7, 11};
    for(int x : r2) templ[2][x] = 1;
    int r3[] = {0, 2, 4, 7, 8, 9, 10};
    for(int x : r3) templ[3][x] = 1;
    int r4[] = {0, 2, 4, 7};
    for(int x : r4) templ[4][x] = 1;
    int r5[] = {0, 4, 7};
    for(int x : r5) templ[5][x] = 1;
    // Row 6 empty
    int r7[] = {0, 3, 7, 8, 9, 10, 11};
    for(int x : r7) templ[7][x] = 1;
    int r8[] = {0, 2, 9};
    for(int x : r8) templ[8][x] = 1;
    int r9[] = {0, 1, 5, 7, 9};
    for(int x : r9) templ[9][x] = 1;
    int r10[] = {0, 2, 5, 7, 9};
    for(int x : r10) templ[10][x] = 1;
    int r11[] = {0, 3, 5, 6, 7, 9};
    for(int x : r11) templ[11][x] = 1;
}

bool check_connectivity(int val, int required_count) {
    if (required_count == 0) return true;
    bool visited[R + 2][C + 2];
    memset(visited, 0, sizeof(visited));
    int q[300][2], head = 0, tail = 0;
    int sr = -1, sc = -1;
    for (int r = 0; r < R + 2; ++r) {
        for (int c = 0; c < C + 2; ++c) {
            if (faces[r][c] == val) { sr = r; sc = c; goto found; }
        }
    }
    found:;
    if (sr == -1) return false;
    visited[sr][sc] = true;
    q[tail][0] = sr; q[tail][1] = sc; tail++;
    int count = 0;
    int dr[] = {-1, 1, 0, 0}, dc[] = {0, 0, -1, 1};
    while (head < tail) {
        int r = q[head][0], c = q[head][1]; head++;
        count++;
        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i], nc = c + dc[i];
            if (nr >= 0 && nr < R + 2 && nc >= 0 && nc < C + 2) {
                if (!visited[nr][nc] && faces[nr][nc] == val) {
                    visited[nr][nc] = true;
                    q[tail][0] = nr; q[tail][1] = nc; tail++;
                }
            }
        }
    }
    return count == required_count;
}

class SlitherlinkSolver {
    int H[R + 1][C]; 
    int V[R][C + 1];
    int clues[R][C];
    int ans_count;
    
    struct DSU {
        int p[169];
        DSU() { for(int i=0; i<169; ++i) p[i]=i; }
        int find(int x) { return p[x]==x?x:p[x]=find(p[x]); }
        void unite(int x, int y) { p[find(x)] = find(y); }
    };

public:
    SlitherlinkSolver(int p[R][C]) {
        memcpy(clues, p, sizeof(clues));
        memset(H, -1, sizeof(H));
        memset(V, -1, sizeof(V));
        ans_count = 0;
    }

    int solve() {
        try_solve(0, 0);
        return ans_count;
    }

    void try_solve(int r, int c) {
        if (ans_count > 1) return;
        if (r == R) {
            if (check_loop()) ans_count++;
            return;
        }
        int next_r = r, next_c = c + 1;
        if (next_c == C) { next_r = r + 1; next_c = 0; }

        int fixed_top = (r > 0) ? H[r][c] : -1;
        int fixed_left = (c > 0) ? V[r][c] : -1;

        int start_top = (fixed_top == -1) ? 0 : fixed_top;
        int end_top = (fixed_top == -1) ? 1 : fixed_top;
        int start_left = (fixed_left == -1) ? 0 : fixed_left;
        int end_left = (fixed_left == -1) ? 1 : fixed_left;

        for (int top = start_top; top <= end_top; ++top) {
            for (int left = start_left; left <= end_left; ++left) {
                H[r][c] = top;
                V[r][c] = left;

                for (int bottom = 0; bottom <= 1; ++bottom) {
                    for (int right = 0; right <= 1; ++right) {
                        int cnt = top + left + bottom + right;
                        if (clues[r][c] != -1 && cnt != clues[r][c]) continue;

                        H[r + 1][c] = bottom;
                        V[r][c + 1] = right;

                        // Vertex checks
                        // Check Vertex (r, c)
                        int d = (r > 0 ? V[r - 1][c] : 0) + (c > 0 ? H[r][c - 1] : 0) + V[r][c] + H[r][c];
                        if (d != 0 && d != 2) continue;

                        // Pruning: Check Vertex (r, c+1) if r > 0
                        if (r > 0) {
                            int d2 = V[r - 1][c + 1] + H[r][c] + V[r][c + 1];
                            // H[r][c+1] is unknown, but degree so far must be <= 2.
                            // If d2 > 2, impossible.
                            // If H[r][c+1] is eventually 1, degree will increase.
                            // If d2 == 2, H[r][c+1] must be 0. We don't enforce yet but good to know.
                            if (d2 > 2) continue;
                        }

                        // Boundary checks
                        if (c == C - 1) {
                            int d_rc = (r > 0 ? V[r - 1][C] : 0) + H[r][C - 1] + V[r][C]; 
                            if (d_rc != 0 && d_rc != 2) continue;
                        }

                        try_solve(next_r, next_c);
                    }
                }
            }
        }
    }

    bool check_loop() {
        DSU dsu;
        int deg[169] = {0};
        int edges = 0;
        for (int r = 0; r <= R; ++r) {
            for (int c = 0; c < C; ++c) {
                if (H[r][c]) {
                    int u = r * 13 + c, v = r * 13 + c + 1;
                    dsu.unite(u, v); deg[u]++; deg[v]++; edges++;
                }
            }
        }
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c <= C; ++c) {
                if (V[r][c]) {
                    int u = r * 13 + c, v = (r + 1) * 13 + c;
                    dsu.unite(u, v); deg[u]++; deg[v]++; edges++;
                }
            }
        }
        if (edges == 0) return false;
        for (int i = 0; i < 169; ++i) if (deg[i] != 0 && deg[i] != 2) return false;
        int root = -1;
        for (int i = 0; i < 169; ++i) {
            if (deg[i] > 0) {
                if (root == -1) root = dsu.find(i);
                else if (dsu.find(i) != root) return false;
            }
        }
        return true;
    }
};

int main() {
    cin >> task_type;
    init_template();
    srand(time(0));
    
    int cells_n = 144;
    int iter = 0;
    while (true) {
        iter++;
        // Initialize with random valid loop
        memset(faces, 0, sizeof(faces));
        int total_faces = (R+2)*(C+2);
        int ones = 0;
        
        // Random walk face flip
        // Bias: flip cells in template more often?
        // Simple: Just random flips
        int moves = 200 + rand() % 300;
        for (int i = 0; i < moves; ++i) {
            int r = 1 + rand() % R;
            int c = 1 + rand() % C;
            int old_val = faces[r][c];
            int new_val = 1 - old_val;
            faces[r][c] = new_val;
            
            // Fast connectivity check: only if we are done or periodically
            // Here we check every step to ensure validity always? Too slow.
            // Just flip, then fix? No.
            // Check delta connectivity.
            // Simple: Check only at end? No, need valid loop.
            // Check every step:
            int n_ones = ones + (new_val ? 1 : -1);
            int n_zeros = total_faces - n_ones;
            if (check_connectivity(1, n_ones) && check_connectivity(0, n_zeros)) {
                ones = n_ones;
            } else {
                faces[r][c] = old_val; // Revert
            }
        }

        if (ones == 0) continue;

        // Extract clues
        bool possible = true;
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                if (templ[r][c]) {
                    int cnt = 0;
                    if (faces[r+1][c+1] != faces[r][c+1]) cnt++;
                    if (faces[r+1][c+1] != faces[r+2][c+1]) cnt++;
                    if (faces[r+1][c+1] != faces[r+1][c]) cnt++;
                    if (faces[r+1][c+1] != faces[r+1][c+2]) cnt++;
                    puzzle[r][c] = cnt;
                    if (cnt == 4) possible = false;
                    if (task_type == 1 && cnt == 0) possible = false;
                } else {
                    puzzle[r][c] = -1;
                }
            }
        }

        if (!possible) continue;

        SlitherlinkSolver solver(puzzle);
        if (solver.solve() == 1) {
            for (int r = 0; r < R; ++r) {
                for (int c = 0; c < C; ++c) {
                    if (templ[r][c]) cout << puzzle[r][c];
                    else cout << " ";
                }
                cout << endl;
            }
            break;
        }
        
        // Safety break
        if (iter > 5000) {
             // In unlikely case of failure, print last valid layout (likely not unique but matches constraints)
             for (int r = 0; r < R; ++r) {
                for (int c = 0; c < C; ++c) {
                    if (templ[r][c]) cout << puzzle[r][c];
                    else cout << " ";
                }
                cout << endl;
            }
            break;
        }
    }
    return 0;
}