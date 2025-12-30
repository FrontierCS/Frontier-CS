#include <iostream>
#include <vector>
#include <utility>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    int len = n / m;
    vector<vector<int>> stacks(m);
    vector<int> pos_stack(n+1), pos_idx(n+1);
    
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < len; j++) {
            int box;
            cin >> box;
            stacks[i].push_back(box);
            pos_stack[box] = i;
            pos_idx[box] = j;
        }
    }
    
    vector<pair<int, int>> ops;
    
    for (int v = 1; v <= n; v++) {
        int s = pos_stack[v];
        int idx = pos_idx[v];
        int depth = (int)stacks[s].size() - idx - 1;
        
        if (depth == 0) {
            // v is already on top
            ops.push_back({v, 0});
            stacks[s].pop_back();
        } else {
            int w = stacks[s][idx+1]; // box directly above v
            int best_d = -1;
            int best_cost = 1e9;
            
            // choose destination stack
            for (int i = 0; i < m; i++) {
                if (i == s) continue;
                int cost = stacks[i].size();
                if (!stacks[i].empty() && stacks[i].back() < w) {
                    cost += 1000 - stacks[i].back();
                }
                if (cost < best_cost) {
                    best_cost = cost;
                    best_d = i;
                } else if (cost == best_cost && i < best_d) {
                    best_d = i;
                }
            }
            
            // move w and all boxes above it to best_d
            ops.push_back({w, best_d + 1});
            
            // extract the block [idx+1, end) from stack s
            vector<int> block;
            for (int j = idx + 1; j < (int)stacks[s].size(); j++) {
                block.push_back(stacks[s][j]);
            }
            
            // update positions for boxes in the block
            int base = stacks[best_d].size();
            for (size_t j = 0; j < block.size(); j++) {
                int box = block[j];
                pos_stack[box] = best_d;
                pos_idx[box] = base + j;
            }
            
            // perform the move
            stacks[best_d].insert(stacks[best_d].end(), block.begin(), block.end());
            stacks[s].resize(idx + 1);
            
            // now v is on top of stack s
            ops.push_back({v, 0});
            stacks[s].pop_back();
        }
    }
    
    // output operations
    for (auto& op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    
    return 0;
}