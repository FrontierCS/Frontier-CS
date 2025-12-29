#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    vector<pair<int,int>> targets;
    int r0, c0;
    cin >> r0 >> c0;
    for (int k = 1; k < M; k++) {
        int i, j;
        cin >> i >> j;
        targets.emplace_back(i, j);
    }
    
    int r = r0, c = c0;
    vector<string> actions;
    
    for (auto &target : targets) {
        int rt = target.first, ct = target.second;
        
        int cost_move = abs(r - rt) + abs(c - ct);
        
        // vertical slide options
        int cost_U = 1 + rt + abs(c - ct);
        int cost_D = 1 + (N-1 - rt) + abs(c - ct);
        int cost_vertical = min(cost_U, cost_D);
        
        // horizontal slide options
        int cost_L = 1 + abs(r - rt) + ct;
        int cost_R = 1 + abs(r - rt) + (N-1 - ct);
        int cost_horizontal = min(cost_L, cost_R);
        
        // two slides to corners
        vector<pair<int,int>> corners = {{0,0}, {0,N-1}, {N-1,0}, {N-1,N-1}};
        int cost_two = 1e9;
        pair<int,int> best_corner;
        for (auto &corner : corners) {
            int cost = 2 + abs(corner.first - rt) + abs(corner.second - ct);
            if (cost < cost_two) {
                cost_two = cost;
                best_corner = corner;
            }
        }
        
        // find minimum cost
        int min_cost = min({cost_move, cost_vertical, cost_horizontal, cost_two});
        
        if (min_cost == cost_move) {
            // move only
            if (rt > r) {
                for (int i = 0; i < rt - r; i++) actions.push_back("M D");
            } else if (rt < r) {
                for (int i = 0; i < r - rt; i++) actions.push_back("M U");
            }
            if (ct > c) {
                for (int i = 0; i < ct - c; i++) actions.push_back("M R");
            } else if (ct < c) {
                for (int i = 0; i < c - ct; i++) actions.push_back("M L");
            }
        } else if (min_cost == cost_vertical) {
            if (cost_U <= cost_D) {
                actions.push_back("S U");
                if (rt > 0) {
                    for (int i = 0; i < rt; i++) actions.push_back("M D");
                }
                if (ct > c) {
                    for (int i = 0; i < ct - c; i++) actions.push_back("M R");
                } else if (ct < c) {
                    for (int i = 0; i < c - ct; i++) actions.push_back("M L");
                }
            } else {
                actions.push_back("S D");
                if (rt < N-1) {
                    for (int i = 0; i < (N-1 - rt); i++) actions.push_back("M U");
                }
                if (ct > c) {
                    for (int i = 0; i < ct - c; i++) actions.push_back("M R");
                } else if (ct < c) {
                    for (int i = 0; i < c - ct; i++) actions.push_back("M L");
                }
            }
        } else if (min_cost == cost_horizontal) {
            if (cost_L <= cost_R) {
                actions.push_back("S L");
                if (rt > r) {
                    for (int i = 0; i < rt - r; i++) actions.push_back("M D");
                } else if (rt < r) {
                    for (int i = 0; i < r - rt; i++) actions.push_back("M U");
                }
                if (ct > 0) {
                    for (int i = 0; i < ct; i++) actions.push_back("M R");
                }
            } else {
                actions.push_back("S R");
                if (rt > r) {
                    for (int i = 0; i < rt - r; i++) actions.push_back("M D");
                } else if (rt < r) {
                    for (int i = 0; i < r - rt; i++) actions.push_back("M U");
                }
                if (ct < N-1) {
                    for (int i = 0; i < (N-1 - ct); i++) actions.push_back("M L");
                }
            }
        } else {
            int ci = best_corner.first, cj = best_corner.second;
            if (ci == 0) actions.push_back("S U");
            else actions.push_back("S D");
            if (cj == 0) actions.push_back("S L");
            else actions.push_back("S R");
            if (rt > ci) {
                for (int i = 0; i < rt - ci; i++) actions.push_back("M D");
            } else if (rt < ci) {
                for (int i = 0; i < ci - rt; i++) actions.push_back("M U");
            }
            if (ct > cj) {
                for (int i = 0; i < ct - cj; i++) actions.push_back("M R");
            } else if (ct < cj) {
                for (int i = 0; i < cj - ct; i++) actions.push_back("M L");
            }
        }
        
        r = rt;
        c = ct;
    }
    
    for (string &act : actions) {
        cout << act << "\n";
    }
    
    return 0;
}