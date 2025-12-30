#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <chrono>
#include <algorithm>
#include <cstring>

using namespace std;

const int ROWS = 8;
const int COLS = 14;
const int LIMIT = 200000;  // maximum number to test per grid
const int TIME_LIMIT = 55; // seconds to search

// Directions: 8 neighbors
const int dr[8] = {-1, -1, -1, 0, 0, 1, 1, 1};
const int dc[8] = {-1, 0, 1, -1, 1, -1, 0, 1};

// Check if number n can be read from grid.
// Precomputed positions for each digit.
bool canRead(int n, const vector<string>& grid,
             const vector<vector<pair<int,int>>>& pos) {
    string s = to_string(n);
    int len = s.size();
    // DP arrays: current reachable cells
    vector<vector<bool>> cur(ROWS, vector<bool>(COLS, false));
    int first_digit = s[0] - '0';
    for (auto& p : pos[first_digit]) {
        cur[p.first][p.second] = true;
    }
    for (int i = 1; i < len; ++i) {
        vector<vector<bool>> next(ROWS, vector<bool>(COLS, false));
        int d = s[i] - '0';
        for (auto& p : pos[d]) {
            int r = p.first, c = p.second;
            // Check if any neighbor is reachable in cur
            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS && cur[nr][nc]) {
                    next[r][c] = true;
                    break;
                }
            }
        }
        cur.swap(next);
        // If no cell is reachable, early exit
        bool any = false;
        for (int r = 0; r < ROWS; ++r)
            for (int c = 0; c < COLS; ++c)
                if (cur[r][c]) { any = true; break; }
        if (!any) return false;
    }
    // Check if any cell is reachable after processing all digits
    for (int r = 0; r < ROWS; ++r)
        for (int c = 0; c < COLS; ++c)
            if (cur[r][c]) return true;
    return false;
}

// Evaluate grid: return the smallest number that cannot be read, up to LIMIT.
int evaluate(const vector<string>& grid) {
    // Precompute positions of each digit
    vector<vector<pair<int,int>>> pos(10);
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            int d = grid[r][c] - '0';
            pos[d].emplace_back(r, c);
        }
    }
    for (int n = 1; n <= LIMIT; ++n) {
        if (!canRead(n, grid, pos)) {
            return n - 1; // score X
        }
    }
    return LIMIT; // all tested numbers can be read
}

// Generate a random grid
vector<string> randomGrid(mt19937& rng) {
    vector<string> grid(ROWS, string(COLS, '0'));
    uniform_int_distribution<int> dist(0, 9);
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            grid[r][c] = '0' + dist(rng);
        }
    }
    return grid;
}

int main() {
    // Setup random number generator
    random_device rd;
    mt19937 rng(rd());
    
    auto start = chrono::steady_clock::now();
    int best_score = 0;
    vector<string> best_grid;
    
    // Search for best grid within time limit
    while (true) {
        auto now = chrono::steady_clock::now();
        auto elapsed = chrono::duration_cast<chrono::seconds>(now - start).count();
        if (elapsed >= TIME_LIMIT) break;
        
        vector<string> grid = randomGrid(rng);
        int score = evaluate(grid);
        if (score > best_score) {
            best_score = score;
            best_grid = grid;
        }
    }
    
    // Output the best grid found
    for (const string& row : best_grid) {
        cout << row << '\n';
    }
    
    return 0;
}