#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <set>

char query(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    char response;
    std::cin >> response;
    return response;
}

void answer(const std::vector<int>& a) {
    std::cout << "!";
    for (size_t i = 1; i < a.size(); ++i) {
        std::cout << " " << a[i];
    }
    std::cout << std::endl;
}

struct Assignment {
    int p1, p2, p3;
};

std::vector<Assignment> initial_assignments;
std::vector<int> c_placeholder = {1, 2, 3, 4, 5};

bool is_valid(const Assignment& a) {
    // A_i \in {c1,c2,c3}
    if (a.p1 != c_placeholder[0] && a.p1 != c_placeholder[1] && a.p1 != c_placeholder[2]) return false;
    
    // A_{i+1} candidates
    std::vector<int> c_p2_cand;
    for (int j = 0; j < 4; ++j) {
        if (c_placeholder[j] != a.p1) {
            c_p2_cand.push_back(c_placeholder[j]);
        }
    }
    if (a.p2 != c_p2_cand[0] && a.p2 != c_p2_cand[1] && a.p2 != c_p2_cand[2]) return false;

    // A_{i+2} candidates
    std::vector<int> c_p3_cand;
    for (int val : c_p2_cand) {
        if (val != a.p2) {
            c_p3_cand.push_back(val);
        }
    }
    c_p3_cand.push_back(c_placeholder[4]);
    std::sort(c_p3_cand.begin(), c_p3_cand.end());
    
    bool p3_ok = false;
    for(int j=0; j<3; ++j) {
        if (a.p3 == c_p3_cand[j]) {
            p3_ok = true;
            break;
        }
    }
    if (!p3_ok) return false;

    return true;
}

void generate_assignments() {
    std::vector<int> p = {1, 2, 3, 4, 5};
    std::sort(p.begin(), p.end());
    do {
        Assignment a = {p[0], p[1], p[2]};
        if (is_valid(a)) {
            initial_assignments.push_back(a);
        }
    } while (std::next_permutation(p.begin(), p.end()));
}

struct Node {
    int p, q;
    Node *left = nullptr, *right = nullptr;
    Assignment final_assignment;
};

Node* build_tree(std::vector<Assignment>& assignments) {
    Node* node = new Node();
    if (assignments.size() <= 1) {
        if (!assignments.empty()) {
            node->final_assignment = assignments[0];
        }
        return node;
    }

    int best_p = -1, best_q = -1;
    size_t min_max_size = assignments.size();

    int queries[3][2] = {{1, 2}, {1, 3}, {2, 3}};
    for (auto& q_pair : queries) {
        int p_idx = q_pair[0], q_idx = q_pair[1];
        
        std::vector<Assignment> left_group, right_group;
        for (const auto& a : assignments) {
            int val_p = (p_idx == 1) ? a.p1 : ((p_idx == 2) ? a.p2 : a.p3);
            int val_q = (q_idx == 1) ? a.p1 : ((q_idx == 2) ? a.p2 : a.p3);
            if (val_p < val_q) {
                left_group.push_back(a);
            } else {
                right_group.push_back(a);
            }
        }

        size_t max_size = std::max(left_group.size(), right_group.size());
        if (max_size < min_max_size) {
            min_max_size = max_size;
            best_p = p_idx;
            best_q = q_idx;
        }
    }

    node->p = best_p;
    node->q = best_q;
    
    std::vector<Assignment> left_group, right_group;
    for (const auto& a : assignments) {
        int val_p = (best_p == 1) ? a.p1 : ((best_p == 2) ? a.p2 : a.p3);
        int val_q = (best_q == 1) ? a.p1 : ((best_q == 2) ? a.p2 : a.p3);
        if (val_p < val_q) {
            left_group.push_back(a);
        } else {
            right_group.push_back(a);
        }
    }
    
    node->left = build_tree(left_group);
    node->right = build_tree(right_group);
    
    return node;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    generate_assignments();
    Node* decision_tree = build_tree(initial_assignments);

    std::vector<int> a(n + 1);
    std::set<int> unassigned_values;
    for (int i = 1; i <= n; ++i) {
        unassigned_values.insert(i);
    }
    
    int i = 1;
    for (; i <= n - 4; i += 3) {
        std::vector<int> current_c;
        auto it = unassigned_values.begin();
        for(int k=0; k<5; ++k) {
            current_c.push_back(*it);
            ++it;
        }

        Node* current_node = decision_tree;
        while(current_node->left != nullptr) {
            int p_idx = current_node->p;
            int q_idx = current_node->q;
            int pos1 = i + p_idx - 1;
            int pos2 = i + q_idx - 1;
            
            char res = query(pos1, pos2);

            if (res == '<') {
                current_node = current_node->left;
            } else {
                current_node = current_node->right;
            }
        }
        Assignment relative_a = current_node->final_assignment;
        a[i] = current_c[relative_a.p1 - 1];
        a[i+1] = current_c[relative_a.p2 - 1];
        a[i+2] = current_c[relative_a.p3 - 1];

        unassigned_values.erase(a[i]);
        unassigned_values.erase(a[i+1]);
        unassigned_values.erase(a[i+2]);
    }
    
    int rem_count = n - i + 1;
    if (rem_count > 0) {
        std::vector<int> rem_indices;
        for (int j=i; j<=n; ++j) rem_indices.push_back(j);
        
        std::vector<int> rem_values;
        for (int val : unassigned_values) rem_values.push_back(val);
        
        std::sort(rem_indices.begin(), rem_indices.end(), [](int p1, int p2){
            return query(p1, p2) == '<';
        });

        for(int k=0; k < rem_count; ++k) {
            a[rem_indices[k]] = rem_values[k];
        }
    }
    
    answer(a);

    return 0;
}