#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

// Grid size
const int N = 30;

// Tile types and rotations
int tiles[N][N];
int rot[N][N];
int best_rot[N][N];
int mate[8][4][4]; // [type][rotation][port] -> connected port

// Directions: 0:Left, 1:Up, 2:Right, 3:Down
int di[] = {0, -1, 0, 1};
int dj[] = {-1, 0, 1, 0};

// Precompute internal connections for all types and rotations
void precompute() {
    vector<vector<pair<int,int>>> base(8);
    // Base connections for rotation 0
    base[0] = {{0,1}};         // L-U
    base[1] = {{0,3}};         // L-D
    base[2] = {{2,3}};         // R-D
    base[3] = {{1,2}};         // U-R
    base[4] = {{0,1}, {2,3}};  // L-U, R-D
    base[5] = {{0,3}, {1,2}};  // L-D, U-R
    base[6] = {{0,2}};         // L-R
    base[7] = {{1,3}};         // U-D

    for(int t=0; t<8; ++t) {
        for(int r=0; r<4; ++r) {
            for(int p=0; p<4; ++p) mate[t][r][p] = -1;
            for(auto p : base[t]) {
                int u = p.first;
                int v = p.second;
                // If port u is connected to v in rot 0,
                // In rot r (CCW), the feature at u moves to (u - r + 4) % 4.
                int u_prime = (u - r + 4) % 4;
                int v_prime = (v - r + 4) % 4;
                mate[t][r][u_prime] = v_prime;
                mate[t][r][v_prime] = u_prime;
            }
        }
    }
}

// Visited array for path tracing
int visited[N][N][4];
int gen = 0;
long long best_score_real = -1;

// Function to evaluate the current configuration
long long evaluate() {
    gen++;
    vector<int> loops;
    long long total_len = 0;
    
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            for(int p=0; p<4; ++p) {
                if(visited[i][j][p] == gen) continue;
                
                int t = tiles[i][j];
                int r = rot[i][j];
                // Check if this port has an internal connection
                if(mate[t][r][p] == -1) {
                    visited[i][j][p] = gen;
                    continue;
                }
                
                // Trace path
                int start_i = i, start_j = j, start_p = p;
                int ci = i, cj = j, cp = p;
                int len = 0;
                bool is_loop = false;
                
                while(true) {
                    // If we hit a visited port in current generation
                    if(visited[ci][cj][cp] == gen) {
                        // If it is the start, we found a loop
                        if(ci == start_i && cj == start_j && cp == start_p) {
                            is_loop = true;
                        }
                        break;
                    }
                    
                    visited[ci][cj][cp] = gen;
                    int ct = tiles[ci][cj];
                    int cr = rot[ci][cj];
                    int exit_p = mate[ct][cr][cp];
                    
                    if(exit_p == -1) break; // Should not happen given initial check
                    visited[ci][cj][exit_p] = gen; // Mark exit port as visited too
                    
                    // Move to neighbor
                    int ni = ci + di[exit_p];
                    int nj = cj + dj[exit_p];
                    
                    // Check boundary
                    if(ni < 0 || ni >= N || nj < 0 || nj >= N) break;
                    
                    // Enter neighbor at opposite port
                    int np = (exit_p + 2) % 4;
                    int nt = tiles[ni][nj];
                    int nr = rot[ni][nj];
                    
                    // Check if neighbor connects back
                    if(mate[nt][nr][np] == -1) break;
                    
                    ci = ni; cj = nj; cp = np;
                    len++;
                }
                
                if(is_loop) loops.push_back(len);
                else total_len += len;
            }
        }
    }
    
    sort(loops.rbegin(), loops.rend());
    long long L1 = (loops.size() > 0) ? loops[0] : 0;
    long long L2 = (loops.size() > 1) ? loops[1] : 0;
    
    long long real_score = L1 * L2;
    // Keep track of the best solution found
    if(real_score > best_score_real) {
        best_score_real = real_score;
        for(int r=0; r<N; ++r) 
            for(int c=0; c<N; ++c) 
                best_rot[r][c] = rot[r][c];
    }
    
    // Heuristic score for optimization
    long long h_score = 0;
    if(L2 > 0) {
        h_score = L1 * L2 * 1000 + L1 + L2 + total_len;
    } else if(L1 > 0) {
        h_score = L1 * 1000 + total_len;
    } else {
        h_score = total_len;
    }
    return h_score;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    precompute();
    
    // Input reading
    for(int i=0; i<N; ++i) {
        string s; cin >> s;
        for(int j=0; j<N; ++j) {
            tiles[i][j] = s[j] - '0';
        }
    }
    
    // Random initialization
    mt19937 rng(12345);
    for(int i=0; i<N; ++i) 
        for(int j=0; j<N; ++j) 
            rot[i][j] = rng() % 4;
            
    best_score_real = -1;
    long long current_h_score = evaluate();
    
    // Hill Climbing with time limit
    auto start_time = chrono::steady_clock::now();
    double TL = 1.85; // slightly less than 2.0s
    
    int iters = 0;
    while(true) {
        iters++;
        if((iters & 511) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if(elapsed > TL) break;
        }
        
        int r = rng() % N;
        int c = rng() % N;
        int old_rot = rot[r][c];
        int new_rot = (old_rot + 1 + (rng() % 3)) % 4; // pick distinct rotation
        
        rot[r][c] = new_rot;
        long long new_h_score = evaluate();
        
        // Accept improvement or equality
        if(new_h_score >= current_h_score) {
            current_h_score = new_h_score;
        } else {
            rot[r][c] = old_rot; // Revert
        }
    }
    
    // Output best configuration
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            cout << best_rot[i][j];
        }
    }
    cout << endl;
    
    return 0;
}