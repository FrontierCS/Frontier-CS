#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <list>

using namespace std;

// Data structure for managing misplaced elements efficiently.
// It uses a combination of a boolean vector, a list, and a vector of list iterators
// to achieve O(1) time complexity for additions, deletions, and checks.
struct MisplacedManager {
    vector<bool> is_misplaced;
    list<int> misplaced_list;
    vector<typename list<int>::iterator> list_iters;
    const vector<int>& pos_init;
    const vector<int>& pos;

    MisplacedManager(int n, const vector<int>& pi, const vector<int>& p)
        : is_misplaced(n, false), list_iters(n), pos_init(pi), pos(p) {}

    void init() {
        for (int i = 0; i < is_misplaced.size(); ++i) {
            if (pos[i] != pos_init[i]) {
                misplaced_list.push_front(i);
                is_misplaced[i] = true;
                list_iters[i] = misplaced_list.begin();
            }
        }
    }

    void update(int v) {
        bool should_be_misplaced = (pos[v] != pos_init[v]);
        if (should_be_misplaced && !is_misplaced[v]) {
            misplaced_list.push_front(v);
            is_misplaced[v] = true;
            list_iters[v] = misplaced_list.begin();
        } else if (!should_be_misplaced && is_misplaced[v]) {
            misplaced_list.erase(list_iters[v]);
            is_misplaced[v] = false;
        }
    }

    bool empty() const {
        return misplaced_list.empty();
    }

    int front() const {
        return misplaced_list.front();
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> s(n);
    vector<int> pos_init(n);
    bool sorted = true;
    for (int i = 0; i < n; ++i) {
        cin >> s[i];
        pos_init[s[i]] = i;
        if (s[i] != i) {
            sorted = false;
        }
    }

    int m;
    cin >> m;

    vector<pair<int, int>> jerry_swaps(m);
    for (int i = 0; i < m; ++i) {
        cin >> jerry_swaps[i].first >> jerry_swaps[i].second;
    }

    if (sorted) {
        cout << 0 << endl;
        cout << 0 << endl;
        return 0;
    }

    long long best_v = -1;
    int best_r = -1;
    vector<pair<int, int>> best_swaps;

    int r_max = min(m, 5000);

    for (int r = 1; r <= r_max; ++r) {
        vector<int> pos(n), val(n);
        iota(pos.begin(), pos.end(), 0);
        iota(val.begin(), val.end(), 0);

        MisplacedManager mm(n, pos_init, pos);
        mm.init();
        
        vector<pair<int, int>> current_swaps(r);
        long long total_cost = 0;

        for (int k = r - 1; k >= 0; --k) {
            // Undo Jerry's move by applying the same swap.
            // This transforms the target state for the end of round k
            // to the target state for the beginning of round k.
            int x = jerry_swaps[k].first;
            int y = jerry_swaps[k].second;
            if (x != y) {
                int val_at_x = val[x];
                int val_at_y = val[y];
                swap(val[x], val[y]);
                swap(pos[val_at_x], pos[val_at_y]);
                mm.update(val_at_x);
                mm.update(val_at_y);
            }

            // Decide our move for round k using a greedy heuristic.
            // The heuristic aims to place one misplaced element to its correct initial position.
            if (mm.empty()) {
                current_swaps[k] = {0, 0};
            } else {
                int v_to_fix = mm.front();
                int val_a = v_to_fix;
                int val_b = val[pos_init[v_to_fix]];
                
                int u = pos[val_a];
                int v = pos[val_b];
                current_swaps[k] = {u, v};

                if (val_a != val_b) {
                    total_cost += abs(u - v);

                    // Undo our chosen move.
                    // This transforms the target state for the beginning of round k
                    // to the target state for the end of round k-1.
                    swap(val[u], val[v]);
                    swap(pos[val_a], pos[val_b]);
                    mm.update(val_a);
                    mm.update(val_b);
                }
            }
        }
        
        // If all elements are in their correct initial positions after R rounds of backward simulation,
        // this is a valid sequence of swaps.
        if (mm.empty()) {
            long long current_v = (long long)r * total_cost;
            if (best_v == -1 || current_v < best_v) {
                best_v = current_v;
                best_r = r;
                best_swaps = current_swaps;
            }
        }
    }

    cout << best_r << endl;
    for (int i = 0; i < best_r; ++i) {
        cout << best_swaps[i].first << " " << best_swaps[i].second << endl;
    }
    cout << best_v << endl;

    return 0;
}