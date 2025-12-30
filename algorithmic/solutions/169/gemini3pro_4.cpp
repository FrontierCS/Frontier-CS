#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Structure to represent a potential move sequence
struct Move {
    char type; // 'L', 'R', 'U', 'D'
    int index; // Row or Column index
    int count; // Number of times to shift
    int removed; // Number of Oni removed by this move
    int cost; // Number of steps (count, or 2*count for restore)
    bool restore; // If true, perform shift then reverse
};

int N;
vector<string> board;

struct Pos {
    int r, c;
};

// Check if an Oni at (r, c) has a safe path to the edge in any direction
bool is_safe(const vector<string>& b, int r, int c) {
    // Check Up
    bool safeU = true;
    for (int k = 0; k < r; ++k) if (b[k][c] == 'o') { safeU = false; break; }
    if (safeU) return true;

    // Check Down
    bool safeD = true;
    for (int k = r + 1; k < N; ++k) if (b[k][c] == 'o') { safeD = false; break; }
    if (safeD) return true;

    // Check Left
    bool safeL = true;
    for (int k = 0; k < c; ++k) if (b[r][k] == 'o') { safeL = false; break; }
    if (safeL) return true;

    // Check Right
    bool safeR = true;
    for (int k = c + 1; k < N; ++k) if (b[r][k] == 'o') { safeR = false; break; }
    if (safeR) return true;

    return false;
}

// Ensure all remaining Oni on the board still have at least one safe direction
bool check_solvable(const vector<string>& b) {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (b[i][j] == 'x') {
                if (!is_safe(b, i, j)) return false;
            }
        }
    }
    return true;
}

// Apply shift operation to the board
void apply_shift(vector<string>& b, char type, int idx, int count) {
    for (int k = 0; k < count; ++k) {
        if (type == 'L') {
            for (int j = 0; j < N - 1; ++j) b[idx][j] = b[idx][j+1];
            b[idx][N-1] = '.';
        } else if (type == 'R') {
            for (int j = N - 1; j > 0; --j) b[idx][j] = b[idx][j-1];
            b[idx][0] = '.';
        } else if (type == 'U') {
            for (int i = 0; i < N - 1; ++i) b[i][idx] = b[i+1][idx];
            b[N-1][idx] = '.';
        } else if (type == 'D') {
            for (int i = N - 1; i > 0; --i) b[i][idx] = b[i-1][idx];
            b[0][idx] = '.';
        }
    }
}

// Evaluate a permanent "Purge" move (shifting until Oni fall off)
// Returns {removed Oni count, shift amount}
pair<int, int> evaluate_purge(const vector<string>& b, char type, int idx) {
    int limit = 0;
    vector<int> oni_indices;
    
    if (type == 'L') {
        limit = N;
        for (int j = 0; j < N; ++j) if (b[idx][j] == 'o') { limit = j; break; }
        for (int j = 0; j < limit; ++j) if (b[idx][j] == 'x') oni_indices.push_back(j);
        if (oni_indices.empty()) return {0, 0};
        int last_oni = oni_indices.back();
        return {(int)oni_indices.size(), last_oni + 1};
    } 
    else if (type == 'R') {
        limit = -1;
        for (int j = N - 1; j >= 0; --j) if (b[idx][j] == 'o') { limit = j; break; }
        for (int j = N - 1; j > limit; --j) if (b[idx][j] == 'x') oni_indices.push_back(j);
        if (oni_indices.empty()) return {0, 0};
        int furthest_oni = oni_indices.back(); // Smallest index > limit
        return {(int)oni_indices.size(), N - furthest_oni};
    }
    else if (type == 'U') {
        limit = N;
        for (int i = 0; i < N; ++i) if (b[i][idx] == 'o') { limit = i; break; }
        for (int i = 0; i < limit; ++i) if (b[i][idx] == 'x') oni_indices.push_back(i);
        if (oni_indices.empty()) return {0, 0};
        int last_oni = oni_indices.back();
        return {(int)oni_indices.size(), last_oni + 1};
    }
    else if (type == 'D') {
        limit = -1;
        for (int i = N - 1; i >= 0; --i) if (b[i][idx] == 'o') { limit = i; break; }
        for (int i = N - 1; i > limit; --i) if (b[i][idx] == 'x') oni_indices.push_back(i);
        if (oni_indices.empty()) return {0, 0};
        int furthest_oni = oni_indices.back(); 
        return {(int)oni_indices.size(), N - furthest_oni};
    }
    return {0, 0};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cin >> N;
    board.resize(N);
    for (int i = 0; i < N; ++i) cin >> board[i];
    
    vector<pair<char, int>> moves_out;
    
    while (true) {
        int oni_count = 0;
        vector<Pos> oni_list;
        for(int i=0;i<N;++i) for(int j=0;j<N;++j) if(board[i][j]=='x') {
            oni_count++;
            oni_list.push_back({i,j});
        }
        
        if (oni_count == 0) break;
        
        // Find best move based on score: removed * 1000 - cost
        Move bestMove = {' ', -1, -1, -1, 1000000, false};
        double bestScore = -1e18;
        
        // 1. Consider Purge Moves (permanent shifts)
        for (int i = 0; i < N; ++i) {
            char types[] = {'L', 'R', 'U', 'D'};
            for (char t : types) {
                pair<int, int> res = evaluate_purge(board, t, i);
                if (res.first > 0) {
                    vector<string> next_b = board;
                    apply_shift(next_b, t, i, res.second);
                    
                    // Crucial: Only accept purge if it doesn't trap any remaining Oni
                    if (check_solvable(next_b)) {
                        double score = res.first * 1000.0 - res.second;
                        if (score > bestScore) {
                            bestScore = score;
                            bestMove = {t, i, res.second, res.first, res.second, false};
                        }
                    }
                }
            }
        }
        
        // 2. Consider Shift-Restore Moves (safe fallback)
        for (auto p : oni_list) {
            int r = p.r;
            int c = p.c;
            
            bool safeU = true;
            for(int k=0; k<r; ++k) if(board[k][c] == 'o') { safeU = false; break; }
            if (safeU) {
                int cost = 2 * (r + 1);
                double score = 1 * 1000.0 - cost;
                if (score > bestScore) {
                    bestScore = score;
                    bestMove = {'U', c, r + 1, 1, cost, true};
                }
            }
            
            bool safeD = true;
            for(int k=r+1; k<N; ++k) if(board[k][c] == 'o') { safeD = false; break; }
            if (safeD) {
                int cost = 2 * (N - r);
                double score = 1 * 1000.0 - cost;
                if (score > bestScore) {
                    bestScore = score;
                    bestMove = {'D', c, N - r, 1, cost, true};
                }
            }
            
            bool safeL = true;
            for(int k=0; k<c; ++k) if(board[r][k] == 'o') { safeL = false; break; }
            if (safeL) {
                int cost = 2 * (c + 1);
                double score = 1 * 1000.0 - cost;
                if (score > bestScore) {
                    bestScore = score;
                    bestMove = {'L', r, c + 1, 1, cost, true};
                }
            }
            
            bool safeR = true;
            for(int k=c+1; k<N; ++k) if(board[r][k] == 'o') { safeR = false; break; }
            if (safeR) {
                int cost = 2 * (N - c);
                double score = 1 * 1000.0 - cost;
                if (score > bestScore) {
                    bestScore = score;
                    bestMove = {'R', r, N - c, 1, cost, true};
                }
            }
        }
        
        if (bestMove.removed == -1) break; // Should not happen
        
        if (bestMove.restore) {
            char reverseType;
            if (bestMove.type == 'L') reverseType = 'R';
            else if (bestMove.type == 'R') reverseType = 'L';
            else if (bestMove.type == 'U') reverseType = 'D';
            else reverseType = 'U';
            
            for (int k = 0; k < bestMove.count; ++k) moves_out.push_back({bestMove.type, bestMove.index});
            apply_shift(board, bestMove.type, bestMove.index, bestMove.count);
            
            for (int k = 0; k < bestMove.count; ++k) moves_out.push_back({reverseType, bestMove.index});
            apply_shift(board, reverseType, bestMove.index, bestMove.count);
        } else {
            for (int k = 0; k < bestMove.count; ++k) moves_out.push_back({bestMove.type, bestMove.index});
            apply_shift(board, bestMove.type, bestMove.index, bestMove.count);
        }
    }
    
    for (auto m : moves_out) {
        cout << m.first << " " << m.second << "\n";
    }
    
    return 0;
}