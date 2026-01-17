#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int initialDeep;
const int K_CONST = 6; 

int query() {
    cout << "query" << endl;
    int d;
    cin >> d;
    return d;
}

bool move(int c) {
    cout << "move " << c << endl;
    int res;
    cin >> res;
    return res == 1;
}

void solve() {
    int curD = initialDeep;
    if (curD == 0) return;
    
    int last_move_in = -1;

    while (curD > 0) {
        int step = min(K_CONST, curD);
        
        int c1;
        if (last_move_in == -1) c1 = 0; 
        else c1 = (last_move_in + 1) % 3;
        
        vector<int> path;
        path.push_back(c1);
        
        for (int i = 1; i < step; ++i) {
            path.push_back((path.back() + 1) % 3);
        }
        
        for (int c : path) {
            if (move(c)) return;
        }
        
        int d_real = query();
        
        // If we went purely Down, depth would be curD + step.
        if (d_real == curD + step) {
            // First move was Down. Backtrack.
            for (int i = step - 1; i >= 0; --i) {
                move(path[i]);
            }
            
            int bad1 = path[0];
            int from = last_move_in;
            
            vector<int> cands;
            for(int c=0; c<3; ++c) {
                if (c != bad1 && c != from) cands.push_back(c);
            }
            
            // Try the first candidate
            int chosen = cands[0];
            
            path.clear();
            path.push_back(chosen);
            for (int i = 1; i < step; ++i) path.push_back((path.back() + 1) % 3);
            
            for (int c : path) {
                if (move(c)) return;
            }
            d_real = query();
            
            if (d_real == curD + step) {
                // Failed again. Must have been the other candidate (only possible if from == -1).
                for (int i = step - 1; i >= 0; --i) move(path[i]);
                
                int real_up = cands[1];
                path.clear();
                path.push_back(real_up);
                for (int i = 1; i < step; ++i) path.push_back((path.back() + 1) % 3);
                
                for (int c : path) {
                    if (move(c)) return;
                }
                d_real = query();
            }
        }
        
        // Up logic
        // j is number of Up moves before deviation
        int diff = curD + step - d_real;
        int j = diff / 2;
        
        if (j == step) {
            curD -= step;
            last_move_in = path.back(); 
        } else {
            // Deviation at index j
            for (int i = step - 1; i >= j; --i) {
                move(path[i]);
            }
            
            int incoming = (j > 0) ? path[j-1] : last_move_in;
            int bad_out = path[j];
            int up_edge = -1;
            for(int c=0; c<3; ++c) {
                if (c != incoming && c != bad_out) {
                    up_edge = c;
                    break;
                }
            }
            
            if (move(up_edge)) return;
            curD = curD - j - 1;
            last_move_in = up_edge;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false); // Just in case, though interaction requires flush
    cin >> initialDeep;
    solve();
    return 0;
}