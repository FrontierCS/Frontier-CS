#include <iostream>
#include <vector>
#include <cstdlib>
#include <ctime>
#include <cassert>

using namespace std;

struct Node {
    int val;
    int priority;
    Node *left, *right, *parent;
    int size;
    Node(int v) : val(v), priority(rand()), left(nullptr), right(nullptr), parent(nullptr), size(1) {}
};

int size(Node* t) {
    return t ? t->size : 0;
}

void update(Node* t) {
    if (!t) return;
    t->size = 1 + size(t->left) + size(t->right);
    if (t->left) t->left->parent = t;
    if (t->right) t->right->parent = t;
}

// split first k nodes into left, rest into right
pair<Node*, Node*> split(Node* t, int k) {
    if (!t) return {nullptr, nullptr};
    int left_size = size(t->left);
    if (k <= left_size) {
        auto [L, R] = split(t->left, k);
        t->left = R;
        if (R) R->parent = t;
        update(t);
        if (L) L->parent = nullptr;
        t->parent = nullptr;
        return {L, t};
    } else {
        auto [L, R] = split(t->right, k - left_size - 1);
        t->right = L;
        if (L) L->parent = t;
        update(t);
        if (R) R->parent = nullptr;
        t->parent = nullptr;
        return {t, R};
    }
}

Node* merge(Node* L, Node* R) {
    if (!L) return R;
    if (!R) return L;
    if (L->priority > R->priority) {
        L->right = merge(L->right, R);
        if (L->right) L->right->parent = L;
        update(L);
        L->parent = nullptr;
        return L;
    } else {
        R->left = merge(L, R->left);
        if (R->left) R->left->parent = R;
        update(R);
        R->parent = nullptr;
        return R;
    }
}

// compute current position (1-indexed) of node in the treap
int get_pos(Node* node) {
    int pos = size(node->left) + 1;
    while (node->parent) {
        if (node == node->parent->right) {
            pos += size(node->parent->left) + 1;
        }
        node = node->parent;
    }
    return pos;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    srand(time(0));

    int n;
    cin >> n;
    vector<int> v(n+1);
    vector<Node*> nodes(n+1);
    Node* root = nullptr;
    for (int i = 1; i <= n; ++i) {
        cin >> v[i];
        nodes[v[i]] = new Node(v[i]);
        root = merge(root, nodes[v[i]]);
    }

    vector<pair<int, int>> moves;
    long long total_cost = 0;

    for (int i = 1; i <= n; ++i) {
        Node* node = nodes[i];
        int cur_pos = get_pos(node);
        if (cur_pos == i) continue;
        // move from cur_pos to i
        auto [left, rest] = split(root, cur_pos - 1);
        auto [mid, right] = split(rest, 1);
        assert(mid == node);
        Node* whole = merge(left, right);
        auto [L, R] = split(whole, i - 1);
        root = merge(merge(L, node), R);
        moves.emplace_back(cur_pos, i);
        total_cost += i;
    }

    long long min_final_cost = (total_cost + 1) * (moves.size() + 1);
    cout << min_final_cost << " " << moves.size() << "\n";
    for (auto [x, y] : moves) {
        cout << x << " " << y << "\n";
    }

    // cleanup (optional)
    // ...

    return 0;
}