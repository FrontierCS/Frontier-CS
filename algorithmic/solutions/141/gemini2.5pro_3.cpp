#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <algorithm>

// DSU structure
struct DSU {
    std::vector<int> parent;
    int components;
    DSU(int n) {
        parent.resize(n + 1);
        std::iota(parent.begin(), parent.end(), 0);
        components = n;
    }
    int find(int i) {
        if (parent[i] == i)
            return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
            components--;
        }
    }
};

int n, k;
DSU* dsu;

char query(int c) {
    std::cout << "? " << c << std::endl;
    char response;
    std::cin >> response;
    return response;
}

void reset() {
    std::cout << "R" << std::endl;
}

// Check if u's cake type is in the set of cake types of bakeries in C
bool test(int u, const std::vector<int>& C) {
    if (C.empty()) {
        return false;
    }
    bool found = false;
    // We can load at most k-1 items from C to test u
    int chunk_size = k -1;
    if (chunk_size == 0) chunk_size = 1;
    
    for (size_t i = 0; i < C.size(); i += chunk_size) {
        reset();
        for (size_t j = i; j < std::min(C.size(), i + chunk_size); ++j) {
            query(C[j]);
        }
        if (query(u) == 'Y') {
            found = true;
            break;
        }
    }
    return found;
}

// Find a bakery in C that has the same cake type as u
// Assumes such a bakery exists
int find_match(int u, const std::vector<int>& C) {
    if (C.size() == 1) {
        return C[0];
    }
    int mid = C.size() / 2;
    std::vector<int> left(C.begin(), C.begin() + mid);
    std::vector<int> right(C.begin() + mid, C.end());
    if (test(u, left)) {
        return find_match(u, left);
    } else {
        return find_match(u, right);
    }
}


void solve_k1() {
    dsu = new DSU(n);
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            query(i);
            if (query(j) == 'Y') {
                dsu->unite(i, j);
            }
        }
    }
}

void solve_general() {
    dsu = new DSU(n);
    int block_size = k / 2;
    if (block_size == 0) block_size = 1;
    int num_blocks = (n + block_size - 1) / block_size;
    std::vector<std::vector<int>> blocks(num_blocks);
    for (int i = 0; i < n; ++i) {
        blocks[i / block_size].push_back(i + 1);
    }
    
    // Intra-block
    for(int i = 0; i < num_blocks; ++i) {
        reset();
        std::vector<int> queried;
        for(int u : blocks[i]) {
            if(query(u) == 'Y') {
                int match = find_match(u, queried);
                dsu->unite(u, match);
            }
            queried.push_back(u);
        }
    }
    
    // Inter-block
    for(int i = 0; i < num_blocks; ++i) {
        for(int j = i + 1; j < num_blocks; ++j) {
            reset();
            for(int u : blocks[i]) {
                query(u);
            }
            std::vector<int> queried_in_i;
            for(int u : blocks[i]) queried_in_i.push_back(u);

            for(int v : blocks[j]) {
                if(query(v) == 'Y') {
                    // Match could be in block i or in previously queried part of block j
                    // For simplicity, we only check against block i, which is sound but might miss some intra-block j relations again.
                    // This is OK as those relations will be re-checked later or not essential for correctness if transitive relations are found.
                    if(test(v, queried_in_i)) {
                       int match = find_match(v, queried_in_i);
                       dsu->unite(v, match);
                    }
                }
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    std::cin >> n >> k;

    if (k == 1) {
        solve_k1();
    } else {
        solve_general();
    }

    std::cout << "! " << dsu->components << std::endl;

    delete dsu;
    return 0;
}