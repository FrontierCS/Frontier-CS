#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

using namespace std;

// Maximum value of N as per constraints. 4096.
const int MAXN = 4100;

int n, q;
int a[MAXN];
int pos_of_val[MAXN];

struct Node {
    int vl, vr;
    vector<int> pos;     // Sorted list of positions of elements in this value range
    vector<int> to_left; // Prefix counts of elements going to the left child
    map<pair<int, int>, int> memo; // Memoization for range queries on 'pos'
} nodes[4 * MAXN];

int set_cnt;
vector<pair<int, int>> operations;

// Builds the segment tree based on values
void build_tree(int idx, int vl, int vr) {
    nodes[idx].vl = vl;
    nodes[idx].vr = vr;
    if (vl == vr) {
        // Leaf node: stores the position of the single value 'vl'
        nodes[idx].pos.push_back(pos_of_val[vl]);
        return;
    }
    int mid = (vl + vr) / 2;
    build_tree(2 * idx, vl, mid);
    build_tree(2 * idx + 1, mid + 1, vr);

    const auto& left_pos = nodes[2 * idx].pos;
    const auto& right_pos = nodes[2 * idx + 1].pos;
    auto& curr_pos = nodes[idx].pos;
    auto& curr_to_left = nodes[idx].to_left;

    curr_pos.reserve(left_pos.size() + right_pos.size());
    curr_to_left.reserve(left_pos.size() + right_pos.size());

    // Merge positions from children and build the to_left prefix array
    size_t i = 0, j = 0;
    while (i < left_pos.size() && j < right_pos.size()) {
        if (left_pos[i] < right_pos[j]) {
            curr_pos.push_back(left_pos[i]);
            int prev = curr_to_left.empty() ? 0 : curr_to_left.back();
            curr_to_left.push_back(prev + 1);
            i++;
        } else {
            curr_pos.push_back(right_pos[j]);
            int prev = curr_to_left.empty() ? 0 : curr_to_left.back();
            curr_to_left.push_back(prev);
            j++;
        }
    }
    while (i < left_pos.size()) {
        curr_pos.push_back(left_pos[i]);
        int prev = curr_to_left.empty() ? 0 : curr_to_left.back();
        curr_to_left.push_back(prev + 1);
        i++;
    }
    while (j < right_pos.size()) {
        curr_pos.push_back(right_pos[j]);
        int prev = curr_to_left.empty() ? 0 : curr_to_left.back();
        curr_to_left.push_back(prev);
        j++;
    }
}

// Recursive function to get set ID for a sub-range of positions at a node
int solve(int idx, int u, int v) {
    if (u > v) return 0;
    
    // Check memoization
    if (nodes[idx].memo.count({u, v})) return nodes[idx].memo[{u, v}];

    // Base case: leaf node (single value)
    if (nodes[idx].vl == nodes[idx].vr) {
        // Return the initial set ID corresponding to the position
        return nodes[idx].pos[0];
    }

    // Determine the range of indices for left and right children
    // Using the precomputed to_left array
    int l_total = nodes[idx].to_left[v];
    int l_before = (u == 0 ? 0 : nodes[idx].to_left[u - 1]);

    int u_l = l_before;
    int v_l = l_total - 1;

    int r_total = (v + 1) - l_total;
    int r_before = u - l_before;

    int u_r = r_before;
    int v_r = r_total - 1;

    // Recursively solve for children
    int id_l = solve(2 * idx, u_l, v_l);
    int id_r = solve(2 * idx + 1, u_r, v_r);

    int res = 0;
    if (id_l && id_r) {
        // Merge results from left and right children
        // Condition g(S_u) < f(S_v) is satisfied because left child has smaller values
        set_cnt++;
        operations.push_back({id_l, id_r});
        res = set_cnt;
    } else {
        // Only one child contributed, pass the ID up
        res = (id_l ? id_l : id_r);
    }
    
    return nodes[idx].memo[{u, v}] = res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> q)) return 0;

    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos_of_val[a[i]] = i;
    }

    set_cnt = n;
    // Build the structure covering values 1 to n
    build_tree(1, 1, n);

    vector<int> results(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        // Query asks for elements with indices in [l, r]
        // nodes[1].pos is always 1...n (sorted indices), so we request range [l-1, r-1]
        results[i] = solve(1, l - 1, r - 1);
    }

    cout << set_cnt << "\n";
    for (const auto& op : operations) {
        cout << op.first << " " << op.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        cout << results[i] << (i == q - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}