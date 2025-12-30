#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Segment Tree to find Max Sum Increasing Subsequence
struct Node {
    int len;
    long long sum;
    int index; // value of the last element

    bool operator<(const Node& other) const {
        if (len != other.len) return len < other.len;
        return sum < other.sum;
    }
};

vector<Node> tree;
int sz;

void update(int p, Node value) {
    p += sz;
    tree[p] = value;
    for (; p > 1; p >>= 1) {
        if (tree[p] < tree[p^1]) tree[p>>1] = tree[p^1];
        else tree[p>>1] = tree[p];
    }
}

Node query(int l, int r) {
    Node res = {0, 0, 0};
    for (l += sz, r += sz; l < r; l >>= 1, r >>= 1) {
        if (l&1) {
            if (res < tree[l]) res = tree[l];
            l++;
        }
        if (r&1) {
            --r;
            if (res < tree[r]) res = tree[r];
        }
    }
    return res;
}

// Block List for O(sqrt(N)) operations
struct Block {
    vector<int> data;
    Block *next;
    Block() : next(nullptr) { data.reserve(1000); }
};

const int BLOCK_LIMIT = 1000; 
vector<Block*> val_to_block; // Map value -> Block containing it

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> v(n);
    for (int i = 0; i < n; ++i) {
        cin >> v[i];
    }

    // 1. Find LIS with Max Sum
    sz = n + 1;
    tree.assign(2 * sz, {0, 0, 0});
    vector<int> parent(n + 1, 0); 
    
    Node best_global = {0, 0, 0};
    int best_end_val = 0;

    for (int x : v) {
        Node best_prev = query(0, x);
        Node curr = {best_prev.len + 1, best_prev.sum + x, x};
        parent[x] = best_prev.index;
        update(x, curr);
        
        if (best_global < curr) {
            best_global = curr;
            best_end_val = x;
        }
    }

    // Reconstruct S (kept elements)
    vector<int> S;
    int curr_val = best_end_val;
    while (curr_val != 0) {
        S.push_back(curr_val);
        curr_val = parent[curr_val];
    }
    reverse(S.begin(), S.end());
    
    // Identify M (moved elements)
    vector<bool> is_in_S(n + 1, false);
    for (int x : S) is_in_S[x] = true;
    
    vector<int> M;
    for (int x : v) {
        if (!is_in_S[x]) M.push_back(x);
    }
    sort(M.rbegin(), M.rend()); // Sort descending

    // 2. Setup Linked Block List
    val_to_block.resize(n + 1, nullptr);
    Block* head = new Block();
    Block* curr_blk = head;
    
    for (int x : v) {
        if (curr_blk->data.size() >= BLOCK_LIMIT) {
            Block* new_blk = new Block();
            curr_blk->next = new_blk;
            curr_blk = new_blk;
        }
        curr_blk->data.push_back(x);
        val_to_block[x] = curr_blk;
    }

    // 3. Process moves
    struct Move { int x, y; };
    vector<Move> moves;
    long long total_move_cost = 0;

    for (int val : M) {
        // Find current position x
        Block* b = val_to_block[val];
        int x = 1;
        Block* it = head;
        while (it != b) {
            x += it->data.size();
            it = it->next;
        }
        
        int idx_in_block = -1;
        for (int i = 0; i < b->data.size(); ++i) {
            if (b->data[i] == val) {
                idx_in_block = i;
                break;
            }
        }
        x += idx_in_block;
        
        // Remove val
        b->data.erase(b->data.begin() + idx_in_block);
        
        // Determine target y
        auto iter = lower_bound(S.begin(), S.end(), val);
        int rank = distance(S.begin(), iter);
        int y = 1 + rank;

        // Insert val at y
        int current_count = 0;
        it = head;
        Block* target_blk = nullptr;
        int target_idx = -1;
        
        while (it != nullptr) {
            if (current_count + it->data.size() >= y) {
                target_blk = it;
                target_idx = y - current_count - 1;
                break;
            }
            current_count += it->data.size();
            it = it->next;
        }
        
        // If appending to the very end
        if (target_blk == nullptr) {
            // Find last block
            target_blk = head;
            while (target_blk->next != nullptr) target_blk = target_blk->next;
            target_idx = target_blk->data.size();
        }

        target_blk->data.insert(target_blk->data.begin() + target_idx, val);
        val_to_block[val] = target_blk;

        moves.push_back({x, y});
        total_move_cost += y;

        // Split block if too large
        if (target_blk->data.size() > 2 * BLOCK_LIMIT) {
            Block* new_blk = new Block();
            int mid = target_blk->data.size() / 2;
            
            // Move second half to new block
            for (int i = mid; i < target_blk->data.size(); ++i) {
                int u = target_blk->data[i];
                new_blk->data.push_back(u);
                val_to_block[u] = new_blk;
            }
            target_blk->data.resize(mid);
            
            new_blk->next = target_blk->next;
            target_blk->next = new_blk;
        }
        
        // Clean up empty block if necessary (except if it's the only one)
        if (b->data.empty() && head->next != nullptr) {
             // Removing from linked list is O(N_blocks) to find prev, acceptable
             if (b == head) {
                 head = head->next;
                 // b is leaked but fine in CP
             } else {
                 Block* prev = head;
                 while (prev->next != b) prev = prev->next;
                 prev->next = b->next;
             }
        }
    }

    long long final_cost = (total_move_cost + 1) * (long long)(moves.size() + 1);
    cout << final_cost << " " << moves.size() << "\n";
    for (const auto& m : moves) {
        cout << m.x << " " << m.y << "\n";
    }

    return 0;
}