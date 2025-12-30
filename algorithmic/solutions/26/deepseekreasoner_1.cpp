#include <bits/stdc++.h>
using namespace std;

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
uniform_int_distribution<int> dist(0, 1e9);

struct Treap {
    struct Node {
        int value, prio, size;
        Node *left, *right, *parent;
        Node(int v) : value(v), prio(dist(rng)), size(1), left(nullptr), right(nullptr), parent(nullptr) {}
    };

    Node* root;
    vector<Node*> nodes; // nodes[value] -> pointer

    Treap() : root(nullptr) {}
    ~Treap() {
        // clean up nodes to avoid memory leak (optional for contest)
        for (Node* node : nodes) delete node;
    }

    static int getSize(Node* t) { return t ? t->size : 0; }

    void update(Node* t) {
        if (!t) return;
        t->size = 1 + getSize(t->left) + getSize(t->right);
        if (t->left) t->left->parent = t;
        if (t->right) t->right->parent = t;
    }

    void split(Node* t, int k, Node*& left, Node*& right) {
        if (!t) {
            left = right = nullptr;
            return;
        }
        int leftSize = getSize(t->left);
        if (k <= leftSize) {
            split(t->left, k, left, t->left);
            right = t;
            if (left) left->parent = nullptr;
        } else {
            split(t->right, k - leftSize - 1, t->right, right);
            left = t;
            if (right) right->parent = nullptr;
        }
        update(t);
    }

    Node* merge(Node* left, Node* right) {
        if (!left) return right;
        if (!right) return left;
        if (left->prio > right->prio) {
            left->right = merge(left->right, right);
            update(left);
            return left;
        } else {
            right->left = merge(left, right->left);
            update(right);
            return right;
        }
    }

    int getPos(Node* node) {
        int pos = getSize(node->left) + 1;
        while (node->parent) {
            Node* p = node->parent;
            if (node == p->right)
                pos += getSize(p->left) + 1;
            node = p;
        }
        return pos;
    }

    void build(const vector<int>& perm) {
        for (Node* node : nodes) delete node;
        nodes.resize(perm.size() + 1, nullptr);
        root = nullptr;
        for (int val : perm) {
            Node* newNode = new Node(val);
            nodes[val] = newNode;
            root = merge(root, newNode);
        }
    }

    void performMove(int x, int y) {
        Node *left1, *mid, *right1;
        split(root, x - 1, left1, mid);
        split(mid, 1, mid, right1);
        Node* rest = merge(left1, right1);
        Node *left2, *right2;
        split(rest, y - 1, left2, right2);
        root = merge(merge(left2, mid), right2);
    }
};

vector<int> computeLIS(const vector<int>& v) {
    int n = v.size();
    vector<int> tail;          // tail[i] = index of the last element of LIS of length i+1
    vector<int> prev(n, -1);   // previous index in LIS for each position
    vector<int> valueAt(n);    // value at index i (already given)

    for (int i = 0; i < n; ++i) {
        int val = v[i];
        auto it = lower_bound(tail.begin(), tail.end(), i,
            [&](int a, int b) { return v[a] < v[b]; });
        if (it == tail.end()) {
            if (!tail.empty()) prev[i] = tail.back();
            tail.push_back(i);
        } else {
            if (it != tail.begin()) prev[i] = *(it - 1);
            *it = i;
        }
    }

    // reconstruct LIS
    vector<int> lisValues;
    int cur = tail.back();
    while (cur != -1) {
        lisValues.push_back(v[cur]);
        cur = prev[cur];
    }
    reverse(lisValues.begin(), lisValues.end());
    return lisValues;
}

struct Result {
    long long finalCost;
    vector<pair<int, int>> moves;
};

Result simulateStrategyA(const vector<int>& perm) {
    int n = perm.size();
    Treap treap;
    treap.build(perm);
    vector<pair<int, int>> moves;
    long long totalCost = 0;

    for (int val = 1; val <= n; ++val) {
        int x = treap.getPos(treap.nodes[val]);
        int y = val;
        if (x != y) {
            moves.emplace_back(x, y);
            totalCost += y;
            treap.performMove(x, y);
        }
    }
    long long finalCost = (totalCost + 1) * (moves.size() + 1);
    return {finalCost, moves};
}

Result simulateStrategyB(const vector<int>& perm) {
    int n = perm.size();
    Treap treap;
    treap.build(perm);
    vector<pair<int, int>> moves;
    long long totalCost = 0;

    for (int val = n; val >= 1; --val) {
        int x = treap.getPos(treap.nodes[val]);
        int y = val;
        if (x != y) {
            moves.emplace_back(x, y);
            totalCost += y;
            treap.performMove(x, y);
        }
    }
    long long finalCost = (totalCost + 1) * (moves.size() + 1);
    return {finalCost, moves};
}

Result simulateStrategyC(const vector<int>& perm) {
    int n = perm.size();
    vector<int> lis = computeLIS(perm);
    vector<bool> inLis(n + 1, false);
    for (int val : lis) inLis[val] = true;

    Treap treap;
    treap.build(perm);
    vector<pair<int, int>> moves;
    long long totalCost = 0;

    for (int val = 1; val <= n; ++val) {
        if (inLis[val]) continue;
        int x = treap.getPos(treap.nodes[val]);
        int prevPos = 0;
        if (val > 1) prevPos = treap.getPos(treap.nodes[val - 1]);
        int y = (x > prevPos) ? prevPos + 1 : prevPos;
        if (x != y) {
            moves.emplace_back(x, y);
            totalCost += y;
            treap.performMove(x, y);
        }
    }
    long long finalCost = (totalCost + 1) * (moves.size() + 1);
    return {finalCost, moves};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> perm(n);
    for (int i = 0; i < n; ++i) cin >> perm[i];

    vector<Result> candidates;
    candidates.push_back(simulateStrategyA(perm));
    candidates.push_back(simulateStrategyB(perm));
    candidates.push_back(simulateStrategyC(perm));

    Result best = candidates[0];
    for (const Result& res : candidates) {
        if (res.finalCost < best.finalCost)
            best = res;
    }

    cout << best.finalCost << " " << best.moves.size() << "\n";
    for (auto [x, y] : best.moves) {
        cout << x << " " << y << "\n";
    }

    return 0;
}