#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

using namespace std;

// Global state
int N;
vector<int> baskets[4]; // 1, 2, 3
vector<pair<int, int>> moves;

// Helper to find position of a ball
int get_basket(int u) {
    for (int b = 1; b <= 3; ++b) {
        for (int x : baskets[b]) {
            if (x == u) return b;
        }
    }
    return -1;
}

// Get center of a basket
int get_center(int b) {
    int k = baskets[b].size();
    if (k == 0) return -1;
    // According to problem: sorted order, center is (k/2 + 1)-th (1-based)
    // baskets are not necessarily sorted in storage, but problem implies value order
    // Since we maintain sorted vectors, just access index.
    // Index 0-based: k/2.
    return baskets[b][k / 2];
}

// Check if moving ball u from src to dst is valid
bool is_valid(int u, int dst) {
    // Condition 1: u must be center of src (checked by caller usually, but good to know)
    int src = get_basket(u);
    if (src == -1) return false;
    if (get_center(src) != u) return false;

    // Condition 2: u must become center of dst
    // Simulate insertion
    vector<int> temp = baskets[dst];
    temp.push_back(u);
    sort(temp.begin(), temp.end());
    int k = temp.size();
    int center = temp[k / 2];
    return center == u;
}

void perform_move(int u, int dst) {
    int src = get_basket(u);
    // Remove u from src
    auto it = find(baskets[src].begin(), baskets[src].end(), u);
    baskets[src].erase(it);
    // Add to dst
    baskets[dst].push_back(u);
    sort(baskets[dst].begin(), baskets[dst].end()); // Keep sorted
    moves.push_back({src, dst});
}

// Generate the order in which balls should arrive at the destination
void get_arrival_order(vector<int>& balls, vector<int>& order) {
    if (balls.empty()) return;
    int k = balls.size();
    int center_idx = k / 2;
    int c = balls[center_idx];
    
    vector<int> subset = balls;
    subset.erase(subset.begin() + center_idx);
    
    get_arrival_order(subset, order);
    order.push_back(c);
}

// Recursive function to move ball u to target
void smart_move(int u, int target, int depth) {
    if (depth > 200) return; // Safety break, though logic should prevent
    int src = get_basket(u);
    if (src == target) return;
    
    int other = 6 - src - target;

    // Step 1: Make u the center of src
    while (get_center(src) != u) {
        int c = get_center(src);
        // Try to move c to other
        if (is_valid(c, other)) {
            perform_move(c, other);
        } else if (is_valid(c, target)) {
            perform_move(c, target);
        } else {
            // Both blocked, must clear 'other' to 'target'
            // To move c to other, we need to fix other.
            // Move center of other to target
            int c_other = get_center(other);
            smart_move(c_other, target, depth + 1);
            // Retry
            if (is_valid(c, other)) perform_move(c, other);
            // Note: If still fail, it implies more complex blockage, 
            // but for this problem structure, usually resolves.
        }
    }

    // Step 2: Move u to target
    if (is_valid(u, target)) {
        perform_move(u, target);
    } else {
        // Target is incompatible. 
        // We need to move blocking balls from target to other.
        // The blocking ball is the center of target.
        int c_target = get_center(target);
        smart_move(c_target, other, depth + 1);
        // Retry
        if (is_valid(u, target)) perform_move(u, target);
    }
}

int main() {
    cin >> N;

    for (int i = 1; i <= N; ++i) {
        baskets[1].push_back(i);
    }

    vector<int> all_balls = baskets[1];
    vector<int> arrival_order;
    get_arrival_order(all_balls, arrival_order);

    for (int u : arrival_order) {
        smart_move(u, 3, 0);
    }

    cout << moves.size() << endl;
    for (auto p : moves) {
        cout << p.first << " " << p.second << endl;
    }

    return 0;
}