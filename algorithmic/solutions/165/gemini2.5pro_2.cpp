#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <tuple>
#include <numeric>

// It's a competitive programming setup, so using namespace std is common.
using namespace std;

// Fast I/O for competitive programming
struct fast_io {
    fast_io() {
        ios_base::sync_with_stdio(false);
        cin.tie(NULL);
    }
} F;

// Struct to represent coordinates on the grid
struct Point {
    int r, c;
};

// Global variables for problem parameters
int N, M;
Point start_pos;
vector<string> A;
vector<string> T;

// Precomputed locations for each character 'A'-'Z'
vector<Point> locations[26];

// Calculate Manhattan distance between two points
int dist(Point p1, Point p2) {
    return abs(p1.r - p2.r) + abs(p1.c - p2.c);
}

// Helper function to calculate the minimum cost to type a given string `s`
// starting from `current_pos`.
// It greedily chooses the closest key for each character.
// Returns a tuple: {total_cost, final_finger_position, sequence_of_moves}
tuple<int, Point, vector<Point>> cost_type(const string& s, Point current_pos) {
    if (s.empty()) {
        return {0, current_pos, {}};
    }
    int total_cost = 0;
    Point pos = current_pos;
    vector<Point> path;
    path.reserve(s.length());
    for (char ch : s) {
        Point best_loc = {-1, -1};
        int min_d = 1e9;
        // Find the instance of the character `ch` on the grid closest to the current finger position
        for (const auto& loc : locations[ch - 'A']) {
            int d = dist(pos, loc);
            if (d < min_d) {
                min_d = d;
                best_loc = loc;
            }
        }
        total_cost += min_d + 1;
        pos = best_loc;
        path.push_back(pos);
    }
    return {total_cost, pos, path};
}

int main() {
    // Read input
    cin >> N >> M;
    cin >> start_pos.r >> start_pos.c;
    A.resize(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    T.resize(M);
    for (int i = 0; i < M; ++i) cin >> T[i];

    // Precompute the grid locations of all characters
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            locations[A[i][j] - 'A'].push_back({i, j});
        }
    }

    // Main greedy algorithm state
    Point current_pos = start_pos;
    string s_tail = "";
    vector<Point> total_path;
    vector<bool> found(M, false);
    int num_found = 0;
    
    // Loop until all M strings are covered
    while (num_found < M) {
        double best_score = 1e18;
        string best_rem_str;
        vector<Point> best_path;
        Point best_end_pos;
        vector<int> best_covered_indices;
        
        // Iterate over all target strings to find the best one to type next
        for (int i = 0; i < M; ++i) {
            if (found[i]) continue;

            // Find the maximum overlap between the current string's tail and the candidate string's prefix
            int max_k = 0;
            if (!s_tail.empty()) {
                // Check for overlaps of length 4 down to 1
                for (int k = min((int)s_tail.length(), 4); k >= 1; --k) {
                    if (s_tail.substr(s_tail.length() - k) == T[i].substr(0, k)) {
                        max_k = k;
                        break;
                    }
                }
            }

            // The part of T[i] that needs to be typed
            string rem_str = T[i].substr(max_k);
            auto [cost, end_pos, path] = cost_type(rem_str, current_pos);

            // Construct a temporary string to check for newly covered targets
            string check_str = s_tail + rem_str;
            
            vector<int> newly_covered_indices;
            for (int j = 0; j < M; ++j) {
                if (!found[j]) {
                    if (check_str.find(T[j]) != string::npos) {
                        newly_covered_indices.push_back(j);
                    }
                }
            }
            
            if (newly_covered_indices.empty()) {
                // This should not happen in a correct implementation, as T[i] itself should be found.
                // But as a safeguard, we skip.
                continue;
            }

            // Greedy heuristic: cost per newly covered string.
            // A small bonus/priority for zero-cost moves (full overlap).
            double score = (cost == 0) ? -1.0 : (double)cost / newly_covered_indices.size();

            // Update the best candidate if the current one has a better score
            if (score < best_score) {
                best_score = score;
                best_rem_str = rem_str;
                best_path = path;
                best_end_pos = end_pos;
                best_covered_indices = newly_covered_indices;
            }
        }
        
        // Update state with the chosen best candidate
        total_path.insert(total_path.end(), best_path.begin(), best_path.end());
        current_pos = best_end_pos;
        
        s_tail += best_rem_str;
        // Keep only the last 4 characters of the constructed string's tail
        if (s_tail.length() > 4) {
            s_tail = s_tail.substr(s_tail.length() - 4);
        }

        // Mark the newly covered strings as found
        for (int idx : best_covered_indices) {
            if (!found[idx]) {
                found[idx] = true;
                num_found++;
            }
        }
    }

    // Output the sequence of moves
    for (const auto& p : total_path) {
        cout << p.r << " " << p.c << endl;
    }

    return 0;
}