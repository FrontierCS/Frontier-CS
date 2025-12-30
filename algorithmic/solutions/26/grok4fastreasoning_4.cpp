#include <bits/stdc++.h>
using namespace std;

struct Node {
  int val, pri, sz;
  Node *l, *r, *p;
  Node(int v) : val(v), pri((rand() << 16) ^ rand()), sz(1), l(nullptr), r(nullptr), p(nullptr) {}
};

int getsz(Node* t) {
  return t ? t->sz : 0;
}

void upd(Node* t) {
  if (t) t->sz = getsz(t->l) + 1 + getsz(t->r);
}

Node* merge(Node* a, Node* b) {
  if (!a) {
    if (b) b->p = nullptr;
    return b;
  }
  if (!b) {
    if (a) a->p = nullptr;
    return a;
  }
  if (a->pri > b->pri) {
    a->r = merge(a->r, b);
    if (a->r) a->r->p = a;
    upd(a);
    return a;
  } else {
    b->l = merge(a, b->l);
    if (b->l) b->l->p = b;
    upd(b);
    return b;
  }
}

void split(Node* t, Node*& l, Node*& r, int key) {
  if (!t) {
    l = r = nullptr;
    return;
  }
  int cur = getsz(t->l) + 1;
  if (key < cur) {
    split(t->l, l, t->l, key);
    if (t->l) t->l->p = t;
    r = t;
  } else {
    split(t->r, t->r, r, key - cur);
    if (t->r) t->r->p = t;
    l = t;
  }
  upd(t);
}

int get_pos(Node* nd) {
  if (!nd) return 0;
  int rank = getsz(nd->l) + 1;
  Node* c = nd;
  while (c->p) {
    Node* par = c->p;
    if (c == par->r) {
      rank += getsz(par->l) + 1;
    }
    c = par;
  }
  return rank;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  srand(time(nullptr));
  int n;
  cin >> n;
  vector<int> v(n + 1);
  for (int i = 1; i <= n; ++i) cin >> v[i];
  vector<Node*> node_of(n + 1, nullptr);
  Node* root = nullptr;
  for (int i = 1; i <= n; ++i) {
    Node* nn = new Node(v[i]);
    node_of[v[i]] = nn;
    Node* temp_l = nullptr, *temp_r = nullptr;
    split(root, temp_l, temp_r, i - 1);
    root = merge(merge(temp_l, nn), temp_r);
  }
  vector<pair<int, int>> moves;
  for (int k = 1; k <= n; ++k) {
    Node* nd = node_of[k];
    int p = get_pos(nd);
    if (p == k) continue;
    moves.emplace_back(p, k);
    // perform left rotate [k, p]
    Node* A = nullptr, *B = nullptr;
    split(root, A, B, k - 1);
    Node* C = nullptr, *D = nullptr;
    split(B, C, D, p - k + 1);
    Node* G = nullptr, *H = nullptr;
    split(C, G, H, p - k);
    Node* Cp = merge(H, G);
    Node* Bp = merge(Cp, D);
    root = merge(A, Bp);
  }
  long long sum = 0;
  for (auto [x, y] : moves) sum += y;
  long long min_cost = (sum + 1LL) * (moves.size() + 1LL);
  cout << min_cost << " " << moves.size() << "\n";
  for (auto [x, y] : moves) cout << x << " " << y << "\n";
  return 0;
}