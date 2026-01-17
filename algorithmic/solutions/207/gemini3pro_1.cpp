#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

struct Move {
    int u, v;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    if (!(cin >> N)) return 0;

    vector<int> S(N);
    for (int i = 0; i < N; ++i) {
        cin >> S[i];
    }

    int M;
    cin >> M;
    vector<pair<int, int>> jerry_moves(M);
    for (int i = 0; i < M; ++i) {
        cin >> jerry_moves[i].first >> jerry_moves[i].second;
    }

    // k_rem represents the minimum number of swaps needed to sort the array.
    // It is equal to N - (number of cycles).
    vector<int> p = S;
    vector<bool> visited(N, false);
    int cycles = 0;
    for (int i = 0; i < N; ++i) {
        if (!visited[i]) {
            cycles++;
            int curr = i;
            while (!visited[curr]) {
                visited[curr] = true;
                curr = p[curr];
            }
        }
    }
    int k_rem = N - cycles;

    // sigma stores current state of array S
    vector<int> sigma = S;
    // inv stores positions of values: inv[v] = index where value v is located
    vector<int> inv(N);
    for (int i = 0; i < N; ++i) {
        inv[sigma[i]] = i;
    }

    // Set of active edges (cost, u). 
    // An entry (cost, u) means at index u we have value sigma[u], 
    // and we can swap indices (u, sigma[u]) with cost |u - sigma[u]| to fix value sigma[u].
    set<pair<int, int>> active_edges;
    for (int i = 0; i < N; ++i) {
        if (sigma[i] != i) {
            active_edges.insert({abs(i - sigma[i]), i});
        }
    }

    vector<Move> my_moves;
    long long total_cost = 0;

    int r = 0;
    // We run until sorted or rounds exhausted
    for (; r < M && k_rem > 0; ++r) {
        // 1. Jerry's move
        int X = jerry_moves[r].first;
        int Y = jerry_moves[r].second;

        if (X != Y) {
            // Remove edges starting at X and Y if they exist
            if (sigma[X] != X) active_edges.erase({abs(X - sigma[X]), X});
            if (sigma[Y] != Y) active_edges.erase({abs(Y - sigma[Y]), Y});
            
            // Perform Jerry's swap on S
            swap(sigma[X], sigma[Y]);
            inv[sigma[X]] = X;
            inv[sigma[Y]] = Y;
            
            // Re-insert edges
            if (sigma[X] != X) active_edges.insert({abs(X - sigma[X]), X});
            if (sigma[Y] != Y) active_edges.insert({abs(Y - sigma[Y]), Y});
        }

        // 2. Our move
        int u_move = 0, v_move = 0;
        bool swapped = false;

        if (!active_edges.empty()) {
            pair<int, int> best = *active_edges.begin();
            int cost = best.first;
            int u = best.second;
            int v = sigma[u]; // target index for the value at u
            
            // Heuristic to decide whether to swap
            long long rem_rounds = M - r;
            long long max_cost = N;
            
            if (k_rem > 0) {
                double ratio = (double)rem_rounds / k_rem;
                if (ratio >= 8.0) max_cost = 1;
                else if (ratio >= 4.0) max_cost = 2;
                else if (ratio >= 2.5) max_cost = 5;
                else if (ratio >= 1.8) max_cost = 15;
                else if (ratio >= 1.4) max_cost = 50;
                else if (ratio >= 1.1) max_cost = 200;
                else max_cost = N;
            }

            if (cost <= max_cost) {
                // Perform swap of indices u and v
                // At index u is value v. At index v is value sigma[v].
                // After swap, index v has value v. Element v is fixed.
                u_move = u;
                v_move = v;
                swapped = true;
            }
        }

        if (swapped) {
            int u = u_move;
            int v = v_move;
            
            if (sigma[u] != u) active_edges.erase({abs(u - sigma[u]), u});
            if (sigma[v] != v) active_edges.erase({abs(v - sigma[v]), v});
            
            swap(sigma[u], sigma[v]);
            inv[sigma[u]] = u;
            inv[sigma[v]] = v;
            
            if (sigma[u] != u) active_edges.insert({abs(u - sigma[u]), u});
            if (sigma[v] != v) active_edges.insert({abs(v - sigma[v]), v});
            
            total_cost += abs(u - v);
            k_rem--; 
        }
        
        my_moves.push_back({u_move, v_move});
    }

    cout << r << "\n";
    for (const auto& move : my_moves) {
        cout << move.u << " " << move.v << "\n";
    }
    
    long long V = (long long)r * total_cost;
    cout << V << "\n";

    return 0;
}