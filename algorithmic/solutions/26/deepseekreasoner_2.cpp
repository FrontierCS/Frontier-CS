#include <bits/stdc++.h>
#include <chrono>
#include <random>
using namespace std;

struct Node {
    int val, prio, sz;
    Node *left, *right, *parent;
    Node(int v) : val(v), prio(rng()), sz(1), left(nullptr), right(nullptr), parent(nullptr) {}
    static mt19937 rng;
};
mt19937 Node::rng(chrono::steady_clock::now().time_since_epoch().count());

int size(Node* t) { return t ? t->sz : 0; }

void update(Node* t) {
    if (t) {
        t->sz = 1 + size(t->left) + size(t->right);
        if (t->left) t->left->parent = t;
        if (t->right) t->right->parent = t;
    }
}

pair<Node*, Node*> split(Node* t, int k) {
    if (!t) return {nullptr, nullptr};
    int left_sz = size(t->left);
    if (left_sz >= k) {
        auto [l, r] = split(t->left, k);
        t->left = r;
        if (r) r->parent = t;
        update(t);
        if (l) l->parent = nullptr;
        return {l, t};
    } else {
        auto [l, r] = split(t->right, k - left_sz - 1);
        t->right = l;
        if (l) l->parent = t;
        update(t);
        if (r) r->parent = nullptr;
        return {t, r};
    }
}

Node* merge(Node* l, Node* r) {
    if (!l) return r;
    if (!r) return l;
    if (l->prio < r->prio) {
        l->right = merge(l->right, r);
        update(l);
        return l;
    } else {
        r->left = merge(l, r->left);
        update(r);
        return r;
    }
}

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

void delete_tree(Node* t) {
    if (!t) return;
    delete_tree(t->left);
    delete_tree(t->right);
    delete t;
}

tuple<long long, int, vector<pair<int, int>>> solve(const vector<int>& v, bool inc) {
    int n = v.size();
    vector<Node*> loc(n + 1);
    Node* root = nullptr;
    for (int i = 0; i < n; ++i) {
        int val = v[i];
        Node* node = new Node(val);
        loc[val] = node;
        root = merge(root, node);
    }

    long long total_cost = 0;
    int moves_count = 0;
    vector<pair<int, int>> moves;

    if (inc) {
        for (int i = 1; i <= n; ++i) {
            Node* node = loc[i];
            int cur = get_pos(node);
            if (cur == i) continue;
            total_cost += i;
            ++moves_count;
            moves.emplace_back(cur, i);
            auto [left, mid_right] = split(root, cur - 1);
            auto [mid, right] = split(mid_right, 1);
            root = merge(left, right);
            auto [left2, right2] = split(root, i - 1);
            root = merge(merge(left2, mid), right2);
        }
    } else {
        for (int i = n; i >= 1; --i) {
            Node* node = loc[i];
            int cur = get_pos(node);
            if (cur == i) continue;
            total_cost += i;
            ++moves_count;
            moves.emplace_back(cur, i);
            auto [left, mid_right] = split(root, cur - 1);
            auto [mid, right] = split(mid_right, 1);
            root = merge(left, right);
            auto [left2, right2] = split(root, i - 1);
            root = merge(merge(left2, mid), right2);
        }
    }

    delete_tree(root);
    return {total_cost, moves_count, moves};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    vector<int> v(n);
    for (int i = 0; i < n; ++i) {
        cin >> v[i];
    }

    auto [cost1, moves1, seq1] = solve(v, true);
    auto [cost2, moves2, seq2] = solve(v, false);

    long long final1 = (cost1 + 1) * (moves1 + 1);
    long long final2 = (cost2 + 1) * (moves2 + 1);

    if (final1 <= final2) {
        cout << final1 << ' ' << moves1 << '\n';
        for (auto [x, y] : seq1) {
            cout << x << ' ' << y << '\n';
        }
    } else {
        cout << final2 << ' ' << moves2 << '\n';
        for (auto [x, y] : seq2) {
            cout << x << ' ' << y << '\n';
        }
    }

    return 0;
}