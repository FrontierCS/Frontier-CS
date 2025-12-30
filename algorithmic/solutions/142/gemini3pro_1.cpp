#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables to store state
int N, M;
vector<int> poles[60]; // Poles 1 to N+1
vector<pair<int, int>> ans;

// Function to perform a move
void move_ball(int x, int y) {
    if (poles[x].empty()) return; 
    ans.push_back({x, y});
    poles[y].push_back(poles[x].back());
    poles[x].pop_back();
}

// Extract operation:
// Rearranges 'target' such that balls satisfying 'keep_pred' end up at the bottom of 'target'.
// Balls NOT satisfying 'keep_pred' end up at the top of 'helper'.
// 'helper' top balls are moved to 'target' top to fill space.
// 'empty_pole' is used as buffer.
// Precondition: target and helper are full (size M), empty_pole is empty.
// Postcondition: target and helper are full, empty_pole is empty.
template <typename F>
void extract(int target, int helper, int empty_pole, F keep_pred) {
    // 1. Move all balls from target to empty_pole
    // Since capacity is M, and target has M balls, this exactly fills empty_pole.
    int cnt = poles[target].size(); 
    for(int i = 0; i < cnt; ++i) {
        move_ball(target, empty_pole);
    }
    
    // 2. Process balls from empty_pole back to target or helper
    while (!poles[empty_pole].empty()) {
        int c = poles[empty_pole].back();
        
        if (keep_pred(c)) {
            // Keep in target
            move_ball(empty_pole, target);
        } else {
            // Reject to helper
            // Algorithm:
            // 1. Move top of helper to target (to make space in helper and fill target)
            // 2. Move rejected ball from empty_pole to helper
            move_ball(helper, target);
            move_ball(empty_pole, helper);
        }
    }
}

// Recursive solver using Divide and Conquer
void solve(vector<int> pole_indices, vector<int> colors) {
    if (colors.size() <= 1 || pole_indices.empty()) return;

    int k = colors.size() / 2;
    // Split colors into Left and Right sets
    vector<int> left_colors;
    vector<int> right_colors;
    for(int i=0; i<k; ++i) left_colors.push_back(colors[i]);
    for(int i=k; i<(int)colors.size(); ++i) right_colors.push_back(colors[i]);
    
    // We need 'k' poles for the left colors
    int left_count = left_colors.size();
    vector<int> left_poles;
    vector<int> right_poles;
    
    for(int i=0; i<left_count; ++i) left_poles.push_back(pole_indices[i]);
    for(int i=left_count; i<(int)pole_indices.size(); ++i) right_poles.push_back(pole_indices[i]);

    int empty_pole = N + 1;
    
    // Helper lambda to check if a color is in left_colors
    auto is_L = [&](int c) {
        for(int x : left_colors) if(x == c) return true;
        return false;
    };
    
    // Helper lambda to check if a color is in right_colors (not L)
    auto is_R = [&](int c) {
        return !is_L(c);
    };

    // Partition logic
    // We want all left_poles to only contain colors from left_colors.
    for (int i : left_poles) {
        while (true) {
            // Check if pole i is already full of L colors
            int L_in_i = 0;
            for(int c : poles[i]) if(is_L(c)) L_in_i++;
            if (L_in_i == M) break; // Done with this pole
            
            // Find a pole j in right_poles that has some L colors
            int j = -1;
            for (int rp : right_poles) {
                int has_L = 0;
                for(int c : poles[rp]) if(is_L(c)) has_L = 1;
                if (has_L) {
                    j = rp;
                    break;
                }
            }
            
            if (j == -1) break; // Should not happen given constraints
            
            // Perform the swap sequence
            // 1. Concentrate L colors in i at the bottom
            extract(i, j, empty_pole, is_L);
            
            // 2. Concentrate R colors in j at the bottom 
            // This step evicts L colors from j to the top of i
            extract(j, i, empty_pole, is_R);
        }
    }

    // Recurse
    solve(left_poles, left_colors);
    solve(right_poles, right_colors);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    for (int i = 1; i <= N; ++i) {
        for (int j = 0; j < M; ++j) {
            int c; cin >> c;
            poles[i].push_back(c);
        }
    }
    // Pole N+1 is initially empty

    vector<int> all_poles(N);
    for(int i=0; i<N; ++i) all_poles[i] = i+1;
    
    vector<int> all_colors(N);
    for(int i=0; i<N; ++i) all_colors[i] = i+1;
    
    solve(all_poles, all_colors);
    
    cout << ans.size() << "\n";
    for (const auto& p : ans) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}