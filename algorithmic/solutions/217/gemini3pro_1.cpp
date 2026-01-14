#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

int N, M;
int total_dangos;

// Interaction function
int query(const vector<int>& subset) {
    if (subset.empty()) return 0;
    cout << "? " << subset.size();
    for (int x : subset) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void answer(const vector<int>& stick) {
    cout << "!";
    for (int x : stick) cout << " " << x;
    cout << endl;
}

// Check if adding x to current_set causes a conflict
// Returns true if NO conflict (x can be added)
// Returns false if CONFLICT (x duplicates a color in current_set)
// Uses the query on U \ (current_set U {x})
bool check(const vector<int>& current_set, int x) {
    static vector<bool> excluded(10005, false);
    for (int y : current_set) excluded[y] = true;
    excluded[x] = true;
    
    vector<int> q_set;
    q_set.reserve(total_dangos);
    for (int i = 1; i <= total_dangos; ++i) {
        if (!excluded[i]) {
            q_set.push_back(i);
        }
    }
    
    for (int y : current_set) excluded[y] = false;
    excluded[x] = false;
    
    if (q_set.empty()) return false; 
    
    int res = query(q_set);
    // If no conflict, min count in complement is M-1.
    // If conflict, min count is M-2.
    return res == M - 1;
}

// Recursively classify candidates that conflict with 'stick'
// stick: list of items in the current partial stick (subset of colors)
// cands: list of items that are known to conflict with 'stick'
// bins: global storage for identified duplicates
// slot_map: maps index in 'stick' to the global color slot ID
void resolve_collisions(const vector<int>& stick, const vector<int>& cands, vector<vector<int>>& bins, const vector<int>& slot_map) {
    if (cands.empty()) return;
    if (stick.size() == 1) {
        int slot = slot_map[0];
        for (int c : cands) bins[slot].push_back(c);
        return;
    }
    
    int mid = stick.size() / 2;
    vector<int> left_stick(stick.begin(), stick.begin() + mid);
    vector<int> right_stick(stick.begin() + mid, stick.end());
    
    vector<int> left_slots(slot_map.begin(), slot_map.begin() + mid);
    vector<int> right_slots(slot_map.begin() + mid, slot_map.end());
    
    vector<int> left_cands, right_cands;
    
    for (int x : cands) {
        // Check against left half
        if (!check(left_stick, x)) {
            // Conflict with left -> belongs to left half
            left_cands.push_back(x);
        } else {
            // No conflict with left -> must belong to right half (since we know it conflicts with total)
            right_cands.push_back(x);
        }
    }
    
    resolve_collisions(left_stick, left_cands, bins, left_slots);
    resolve_collisions(right_stick, right_cands, bins, right_slots);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N >> M)) return 0;
    total_dangos = N * M;
    
    if (M == 1) {
        cout << "!";
        for (int i = 1; i <= N; ++i) cout << " " << i;
        cout << endl;
        return 0;
    }

    vector<int> pool(total_dangos);
    iota(pool.begin(), pool.end(), 1);
    
    mt19937 rng(1337);
    shuffle(pool.begin(), pool.end(), rng);
    
    vector<vector<int>> bins(N); 
    int pool_ptr = 0;
    
    for (int stick_idx = 0; stick_idx < M; ++stick_idx) {
        vector<int> stick(N, 0); 
        vector<int> filled_slots;
        vector<int> stick_items; 
        
        // 1. Fill from bins
        for (int i = 0; i < N; ++i) {
            if (!bins[i].empty()) {
                stick[i] = bins[i].back();
                bins[i].pop_back();
                filled_slots.push_back(i);
                stick_items.push_back(stick[i]);
            }
        }
        
        // 2. Fill remaining from pool
        vector<int> batch_collisions;
        while (stick_items.size() < N && pool_ptr < total_dangos) {
            int x = pool[pool_ptr++];
            
            if (check(stick_items, x)) {
                // New color
                int slot = -1;
                for(int i=0; i<N; ++i) {
                    if (stick[i] == 0) {
                        slot = i;
                        break;
                    }
                }
                stick[slot] = x;
                stick_items.push_back(x);
                filled_slots.push_back(slot);
            } else {
                // Duplicate
                batch_collisions.push_back(x);
            }
        }
        
        resolve_collisions(stick_items, batch_collisions, bins, filled_slots);
        answer(stick_items);
    }

    return 0;
}