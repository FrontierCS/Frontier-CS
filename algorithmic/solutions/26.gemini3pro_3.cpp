#include <iostream>
#include <vector>
#include <algorithm>
#include <list>

using namespace std;

// Fenwick Tree for Range Maximum Query (len, sum) to find Optimal LIS
struct State {
    int len;
    long long sum;
    int idx; // index in v
    bool operator<(const State& other) const {
        if (len != other.len) return len < other.len;
        return sum < other.sum;
    }
};

int n;
vector<State> tree;

void upd(int pos, State val) {
    for (; pos <= n; pos += pos & -pos) {
        if (tree[pos] < val) tree[pos] = val;
    }
}

State qry(int pos) {
    State res = {0, 0, -1};
    for (; pos > 0; pos -= pos & -pos) {
        if (res < tree[pos]) res = tree[pos];
    }
    return res;
}

// Sqrt Decomposition using List of Vectors
// This allows O(sqrt(N)) insert/delete/access by index
const int B = 1000; 
list<vector<int>> blocks;
vector<list<vector<int>>::iterator> where_block; // stores iterator to block for each value

void build_blocks(const vector<int>& v) {
    where_block.resize(n + 1);
    auto it = blocks.end(); 
    for (int i = 0; i < v.size(); ++i) {
        if (i % B == 0) {
            blocks.emplace_back();
            it = prev(blocks.end());
        }
        it->push_back(v[i]);
        where_block[v[i]] = it;
    }
}

int find_index(int val) {
    auto it_blk = where_block[val];
    int idx = 0;
    // Sum sizes of previous blocks
    for (auto it = blocks.begin(); it != it_blk; ++it) {
        idx += it->size();
    }
    // Search in current block
    for (int x : *it_blk) {
        idx++;
        if (x == val) break;
    }
    return idx;
}

void remove_val(int val) {
    auto it_blk = where_block[val];
    vector<int>& blk = *it_blk;
    for (auto it = blk.begin(); it != blk.end(); ++it) {
        if (*it == val) {
            blk.erase(it);
            break;
        }
    }
    if (blk.empty()) {
        blocks.erase(it_blk);
    }
}

void insert_val(int val, int target) {
    int current_pos = 1;
    auto it = blocks.begin();
    // Find the block where 'target' falls
    while (it != blocks.end()) {
        if (current_pos + (int)it->size() > target) {
            break;
        }
        current_pos += it->size();
        ++it;
    }
    
    if (it == blocks.end()) {
        // Should not happen given problem constraints and logic, 
        // but if target is at the very end, append to last block
        if (blocks.empty()) blocks.emplace_back();
        else it = prev(blocks.end());
    }
    
    int offset = target - current_pos;
    it->insert(it->begin() + offset, val);
    where_block[val] = it;
    
    // Split block if it gets too large to maintain efficiency
    if (it->size() > 2 * B) {
        vector<int> new_vec;
        int mid = it->size() / 2;
        new_vec.assign(it->begin() + mid, it->end());
        it->resize(mid);
        
        auto new_it = blocks.insert(next(it), new_vec);
        for (int x : *new_it) {
            where_block[x] = new_it;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    vector<int> v(n);
    for (int i = 0; i < n; ++i) cin >> v[i];

    // Compute Max Sum LIS
    tree.assign(n + 1, {0, 0, -1});
    vector<int> parent(n, -1);
    
    State best_global = {0, 0, -1};
    int best_end_idx = -1;

    for (int i = 0; i < n; ++i) {
        State prev = qry(v[i] - 1);
        State cur = {prev.len + 1, prev.sum + v[i], i};
        parent[i] = prev.idx;
        upd(v[i], cur);
        
        if (best_global < cur) {
            best_global = cur;
            best_end_idx = i;
        }
    }

    // Reconstruct S
    vector<int> S;
    int curr = best_end_idx;
    while (curr != -1) {
        S.push_back(v[curr]);
        curr = parent[curr];
    }
    reverse(S.begin(), S.end());

    // Identify M (elements to move)
    vector<int> M;
    vector<bool> is_in_S(n + 1, false);
    for (int x : S) is_in_S[x] = true;
    for (int x : v) {
        if (!is_in_S[x]) M.push_back(x);
    }
    // Sort M descending to process moves optimally
    sort(M.begin(), M.end(), greater<int>());

    long long total_move_cost = 0;
    vector<pair<int, int>> moves;
    
    build_blocks(v);

    for (int x : M) {
        int cx = find_index(x);
        // Target is relative to S. Since S is sorted and fixed relative order,
        // and we insert M descending, target is just rank in S + 1.
        int cy = (lower_bound(S.begin(), S.end(), x) - S.begin()) + 1;
        
        moves.push_back({cx, cy});
        total_move_cost += cy;
        
        remove_val(x);
        insert_val(x, cy);
    }

    long long final_cost = (total_move_cost + 1) * (moves.size() + 1);
    cout << final_cost << " " << moves.size() << "\n";
    for (auto p : moves) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}