#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>

// Function to send a query and get results
std::vector<int> do_query(const std::vector<int>& q) {
    if (q.empty()) {
        return {};
    }
    std::cout << q.size();
    for (int x : q) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
    std::vector<int> res(q.size());
    for (size_t i = 0; i < q.size(); ++i) {
        std::cin >> res[i];
    }
    return res;
}

// Function to send the answer
void answer(const std::vector<int>& p) {
    std::cout << -1;
    for (int x : p) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int subtask_id, n;
    std::cin >> subtask_id >> n;

    if (n == 1) {
        answer({1});
        return 0;
    }
    if (n == 2) {
        answer({1, 2});
        return 0;
    }

    // Find neighbors of node 1
    std::vector<int> neighbors_of_1;
    if (n > 2) {
        std::vector<int> q1;
        std::vector<int> cands1;
        for(int i = 2; i <= n; ++i) {
            q1.push_back(1);
            q1.push_back(i);
            q1.push_back(i);
            q1.push_back(1);
            cands1.push_back(i);
        }
        std::vector<int> r1 = do_query(q1);
        for(size_t i = 0; i < cands1.size(); ++i) {
            if (r1[i * 4 + 1] == 1) {
                neighbors_of_1.push_back(cands1[i]);
            }
        }
    }


    std::vector<int> p;
    p.push_back(neighbors_of_1[0]);
    p.push_back(1);
    p.push_back(neighbors_of_1[1]);

    std::set<int> used_nodes;
    used_nodes.insert(1);
    used_nodes.insert(p.front());
    used_nodes.insert(p.back());
    
    std::set<int> S; // Track the set of lit lamps

    while(p.size() < n) {
        // Clear S
        if (!S.empty()) {
            std::vector<int> clear_q;
            for (int node : S) {
                clear_q.push_back(node);
            }
            do_query(clear_q);
            S.clear();
        }

        int u = p.back();
        int prev_u = p[p.size() - 2];

        do_query({u, prev_u});
        S.insert(u);
        S.insert(prev_u);

        std::vector<int> cands;
        for (int i = 1; i <= n; ++i) {
            if (used_nodes.find(i) == used_nodes.end()) {
                cands.push_back(i);
            }
        }
        
        std::vector<int> res = do_query(cands);
        for(int c : cands) {
            if (S.count(c)) S.erase(c);
            else S.insert(c);
        }

        int next_node = -1;
        int prev_res = 1; // S = {u, prev_u} has an edge

        for (size_t i = 0; i < cands.size(); ++i) {
            if (res[i] == 1 && prev_res == 0) {
                next_node = cands[i];
                break;
            }
            prev_res = res[i];
        }
        
        // If the above logic fails (e.g., multiple new edges form),
        // we might not find a next_node. Fallback to a simpler check.
        if (next_node == -1) {
            // After the query, S = {u, prev_u} U cands.
            // Let's find the first candidate that creates an edge with u.
            
            // First, clear S again.
            std::vector<int> clear_q;
            for(int node : S) clear_q.push_back(node);
            do_query(clear_q);
            S.clear();

            do_query({u}); // S = {u}
            S.insert(u);
            
            std::vector<int> res2 = do_query(cands);
            for(int c : cands) {
                if (S.count(c)) S.erase(c);
                else S.insert(c);
            }
            
            for(size_t i = 0; i < res2.size(); ++i) {
                if (res2[i] == 1) {
                    // cand[i] is adjacent to {u, cands[0]...cands[i-1]}
                    // This is likely the neighbor. To be sure, one would need
                    // to check for internal edges, but we'll be optimistic.
                    next_node = cands[i];
                    break;
                }
            }
        }


        p.push_back(next_node);
        used_nodes.insert(next_node);
    }

    answer(p);

    return 0;
}