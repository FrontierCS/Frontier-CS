#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <set>

using namespace std;

// Global variables for problem data
int N;
vector<int> S;
int M;
vector<pair<int, int>> JerryMoves;

// Structures for simulation
vector<int> Board;         // Board[i] = value currently at index i
vector<int> CurrentDest;   // CurrentDest[i] = target value for index i
vector<int> Pos;           // Pos[v] = current index of value v
vector<int> DestPos;       // DestPos[v] = current index of slot with target value v

// Priority set to pick best swap: stores {cost, value}
// Cost is |Pos[v] - DestPos[v]|
set<pair<int, int>> Options;
vector<int> current_cost; // Track cost for each value to update set

void update_option(int val) {
    if (current_cost[val] != -1) {
        Options.erase({current_cost[val], val});
        current_cost[val] = -1;
    }
    
    if (Pos[val] == DestPos[val]) return; // Already fixed
    
    int cost = abs(Pos[val] - DestPos[val]);
    current_cost[val] = cost;
    Options.insert({cost, val});
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    S.resize(N);
    for (int i = 0; i < N; ++i) cin >> S[i];
    
    if (!(cin >> M)) return 0;
    JerryMoves.resize(M);
    for (int i = 0; i < M; ++i) cin >> JerryMoves[i].first >> JerryMoves[i].second;

    // 1. Precompute final destinations of slots
    // Create a permutation mapping initial index to final index after M Jerry swaps
    vector<int> p(N);
    iota(p.begin(), p.end(), 0);
    for (int i = 0; i < M; ++i) {
        swap(p[JerryMoves[i].first], p[JerryMoves[i].second]);
    }
    
    // 2. Initialize simulation state
    Board = S;
    CurrentDest.resize(N);
    // If a slot i ends up at p[i], then we want the value p[i] to be in slot i initially
    // because that value will travel to p[i], which is correct for sorted array.
    for (int i = 0; i < N; ++i) {
        CurrentDest[i] = p[i];
    }
    
    Pos.resize(N);
    DestPos.resize(N);
    for (int i = 0; i < N; ++i) {
        Pos[Board[i]] = i;
        DestPos[CurrentDest[i]] = i;
    }
    
    current_cost.assign(N, -1);
    for (int i = 0; i < N; ++i) {
        update_option(i);
    }

    // 3. Run simulation
    vector<pair<int, int>> UserMoves;
    UserMoves.reserve(M);
    long long total_dist = 0;

    for (int k = 0; k < M; ++k) {
        // Jerry's move
        int jx = JerryMoves[k].first;
        int jy = JerryMoves[k].second;
        
        if (jx != jy) {
            int valX = Board[jx];
            int valY = Board[jy];
            int destX = CurrentDest[jx];
            int destY = CurrentDest[jy];

            // Swap Board and CurrentDest
            swap(Board[jx], Board[jy]);
            swap(CurrentDest[jx], CurrentDest[jy]);

            // Update Pos and DestPos
            Pos[valX] = jy;
            Pos[valY] = jx;
            DestPos[destX] = jy;
            DestPos[destY] = jx;

            // Update options
            update_option(valX);
            update_option(valY);
            update_option(destX);
            update_option(destY);
        }

        // User's move
        int ux = 0, uy = 0;
        if (!Options.empty()) {
            pair<int, int> best = *Options.begin();
            int val = best.second;
            ux = Pos[val];
            uy = DestPos[val]; // This is where val wants to go
            
            // Perform swap
            if (ux != uy) {
                total_dist += abs(ux - uy);
                
                int valU = Board[ux]; // This is val
                int valV = Board[uy];
                int destU = CurrentDest[ux];
                int destV = CurrentDest[uy]; // This is val

                // Swap Board and CurrentDest
                swap(Board[ux], Board[uy]);
                swap(CurrentDest[ux], CurrentDest[uy]);

                // Update Pos and DestPos
                Pos[valU] = uy;
                Pos[valV] = ux;
                DestPos[destU] = uy;
                DestPos[destV] = ux;

                // Update options
                // valU (val) is now at uy (DestPos[val]), so Pos[val] == DestPos[val], cost 0, removed.
                update_option(valU);
                update_option(valV);
                // destV (val) logic matches above
                update_option(destU);
                update_option(destV);
            }
        }
        UserMoves.push_back({ux, uy});
    }

    // Output
    cout << M << "\n";
    for (const auto& p : UserMoves) {
        cout << p.first << " " << p.second << "\n";
    }
    cout << (long long)M * total_dist << "\n";

    return 0;
}