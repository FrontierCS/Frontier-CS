#include <bits/stdc++.h>
using namespace std;

struct Node {
    vector<int> mags;
    Node* lchild = nullptr;
    Node* rchild = nullptr;
    bool isleaf() const { return lchild == nullptr && rchild == nullptr; }
};

vector<int> get_indices(Node* node) {
    vector<int> res;
    if (node->isleaf()) {
        res = node->mags;
    } else {
        auto left = get_indices(node->lchild);
        auto right = get_indices(node->rchild);
        res.insert(res.end(), left.begin(), left.end());
        res.insert(res.end(), right.begin(), right.end());
    }
    return res;
}

int find_nonzero(Node* node, const vector<int>& ref_idx) {
    int sz_ref = ref_idx.size();
    if (node->isleaf()) {
        int sz = node->mags.size();
        for (int i = 0; i < sz; i++) {
            int k = node->mags[i];
            int f;
            cout << "? 1 " << sz_ref << endl;
            cout << k << endl;
            for (int x : ref_idx) cout << x << " ";
            cout << endl;
            cout.flush();
            cin >> f;
            if (f != 0) {
                return k;
            }
        }
        assert(false);
        return -1;
    } else {
        auto left_idx = get_indices(node->lchild);
        int lsz = left_idx.size();
        int f;
        cout << "? " << lsz << " " << sz_ref << endl;
        for (int x : left_idx) cout << x << " ";
        cout << endl;
        for (int x : ref_idx) cout << x << " ";
        cout << endl;
        cout.flush();
        cin >> f;
        if (f != 0) {
            return find_nonzero(node->lchild, ref_idx);
        } else {
            return find_nonzero(node->rchild, ref_idx);
        }
    }
}

void make_query(const vector<int>& left, const vector<int>& right, int& force) {
    int l = left.size();
    int r = right.size();
    cout << "? " << l << " " << r << endl;
    for (int x : left) cout << x << " ";
    cout << endl;
    for (int x : right) cout << x << " ";
    cout << endl;
    cout.flush();
    cin >> force;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        vector<vector<int>> groups;
        for (int i = 1; i <= n; i += 3) {
            vector<int> g;
            g.push_back(i);
            if (i + 1 <= n) g.push_back(i + 1);
            if (i + 2 <= n) g.push_back(i + 2);
            groups.push_back(g);
        }
        bool found_ref = false;
        int ref = -1;
        size_t gi = 0;
        for (; gi < groups.size(); ++gi) {
            auto& g = groups[gi];
            int sz = g.size();
            if (sz == 1) continue;
            if (sz == 2) {
                int f;
                make_query({g[0]}, {g[1]}, f);
                if (f != 0) {
                    ref = g[0];
                    found_ref = true;
                    break;
                }
            } else {  // sz == 3
                int f12, f13, f23;
                make_query({g[0]}, {g[1]}, f12);
                make_query({g[0]}, {g[2]}, f13);
                make_query({g[1]}, {g[2]}, f23);
                int nonzero_count = 0;
                if (f12 != 0) ++nonzero_count;
                if (f13 != 0) ++nonzero_count;
                if (f23 != 0) ++nonzero_count;
                if (nonzero_count == 0) continue;
                ref = g[0];
                found_ref = true;
                break;
            }
        }
        vector<int> zeros;
        if (found_ref) {
            for (int i = 1; i <= n; ++i) {
                if (i == ref) continue;
                int f;
                make_query({ref}, {i}, f);
                if (f == 0) {
                    zeros.push_back(i);
                }
            }
        } else {
            // second phase
            vector<Node*> current_components;
            for (auto& g : groups) {
                Node* node = new Node();
                node->mags = g;
                current_components.push_back(node);
            }
            Node* ref_node = nullptr;
            Node* drill_ref_node = nullptr;
            bool found_pair = false;
            while (!found_pair && current_components.size() > 1) {
                int c = current_components.size();
                vector<Node*> new_components;
                int paired = (c / 2) * 2;
                for (int p = 0; p < paired; p += 2) {
                    Node* c1 = current_components[p];
                    Node* c2 = current_components[p + 1];
                    auto idx1 = get_indices(c1);
                    auto idx2 = get_indices(c2);
                    int f;
                    make_query(idx1, idx2, f);
                    if (f != 0) {
                        found_pair = true;
                        ref_node = c1;
                        drill_ref_node = c2;
                        // stop processing further pairs
                        break;
                    } else {
                        Node* newn = new Node();
                        newn->lchild = c1;
                        newn->rchild = c2;
                        new_components.push_back(newn);
                    }
                }
                for (int p = paired; p < c; ++p) {
                    new_components.push_back(current_components[p]);
                }
                current_components = new_components;
                if (found_pair) break;
            }
            assert(found_pair);
            auto ref_idx = get_indices(drill_ref_node);
            ref = find_nonzero(ref_node, ref_idx);
            found_ref = true;
            // now classify
            for (int i = 1; i <= n; ++i) {
                if (i == ref) continue;
                int f;
                make_query({ref}, {i}, f);
                if (f == 0) {
                    zeros.push_back(i);
                }
            }
        }
        // output
        cout << "! " << zeros.size();
        for (int z : zeros) {
            cout << " " << z;
        }
        cout << endl;
        cout.flush();
        // clean up memory if needed, but skip
    }
    return 0;
}