#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>

using namespace std;

// Interactive problem query function
// Outputs 0 and the pen index, then flushes and reads the response.
int query_pen(int pen) {
    cout << "0 " << pen << endl;
    int res;
    cin >> res;
    return res;
}

// Function to output the final answer
void answer(int p1, int p2) {
    cout << "1 " << p1 << " " << p2 << endl;
}

// Runs a tournament on a list of pens to find a "winner".
// The winner is likely to have a high amount of initial ink.
int run_tournament(vector<int>& pens) {
    if (pens.empty()) return -1;
    vector<int> current = pens;
    
    // Continue rounds until one pen remains
    while (current.size() > 1) {
        vector<int> next_round;
        for (size_t i = 0; i + 1 < current.size(); i += 2) {
            int u = current[i];
            int v = current[i+1];
            
            // Query u
            int res_u = query_pen(u);
            if (res_u == 0) {
                // u is empty, v advances (v was not queried, so no ink used)
                next_round.push_back(v);
            } else {
                // u has ink. Query v.
                int res_v = query_pen(v);
                if (res_v == 0) {
                    // v is empty, u advances (u used 1 unit)
                    next_round.push_back(u);
                } else {
                    // Both have ink. Arbitrarily pick u to advance.
                    // u used 1 unit, v used 1 unit. v is discarded.
                    next_round.push_back(u);
                }
            }
        }
        // If odd number of pens, the last one advances automatically
        if (current.size() % 2 == 1) {
            next_round.push_back(current.back());
        }
        current = next_round;
    }
    return current[0];
}

void solve() {
    int n;
    cin >> n;
    
    vector<int> p(n);
    iota(p.begin(), p.end(), 0);
    
    // Random shuffle is crucial to ensure the values are well-distributed
    // between the two groups, avoiding cases where one group has all low values.
    random_device rd;
    mt19937 g(rd());
    shuffle(p.begin(), p.end(), g);
    
    // Split pens into two roughly equal groups
    int mid = n / 2;
    vector<int> g1(p.begin(), p.begin() + mid);
    vector<int> g2(p.begin() + mid, p.end());
    
    // Run tournament on each group to find the best candidate from each
    int w1 = run_tournament(g1);
    int w2 = run_tournament(g2);
    
    // The winners of the two tournaments are our chosen pens
    answer(w1, w2);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}