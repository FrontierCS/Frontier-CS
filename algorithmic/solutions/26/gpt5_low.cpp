#include <bits/stdc++.h>
using namespace std;

struct Node {
    int val;
    int pr;
    int sz;
    Node *l, *r, *p;
    Node(int v): val(v), pr((rand()<<16) ^ rand()), sz(1), l(nullptr), r(nullptr), p(nullptr) {}
};

int getsz(Node* t){ return t ? t->sz : 0; }
void upd(Node* t){
    if(!t) return;
    t->sz = 1 + getsz(t->l) + getsz(t->r);
    if(t->l) t->l->p = t;
    if(t->r) t->r->p = t;
}
void setchild(Node* parent, Node* child, bool right){
    if(right) parent->r = child;
    else parent->l = child;
    if(child) child->p = parent;
}
Node* merge(Node* a, Node* b){
    if(!a) { if(b) b->p=nullptr; return b; }
    if(!b) { if(a) a->p=nullptr; return a; }
    if(a->pr > b->pr){
        a->r = merge(a->r, b);
        if(a->r) a->r->p = a;
        upd(a);
        a->p = nullptr;
        return a;
    } else {
        b->l = merge(a, b->l);
        if(b->l) b->l->p = b;
        upd(b);
        b->p = nullptr;
        return b;
    }
}
pair<Node*, Node*> split(Node* t, int k){ // first k nodes to left
    if(!t) return {nullptr, nullptr};
    if(getsz(t->l) >= k){
        auto pr = split(t->l, k);
        t->l = pr.second;
        if(t->l) t->l->p = t;
        upd(t);
        if(pr.first) pr.first->p = nullptr;
        return {pr.first, t};
    } else {
        auto pr = split(t->r, k - getsz(t->l) - 1);
        t->r = pr.first;
        if(t->r) t->r->p = t;
        upd(t);
        if(pr.second) pr.second->p = nullptr;
        return {t, pr.second};
    }
}

int getIndex(Node* u){
    int idx = getsz(u->l) + 1;
    while(u->p){
        if(u == u->p->r){
            idx += getsz(u->p->l) + 1;
        }
        u = u->p;
    }
    return idx;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> v(n);
    for(int i=0;i<n;i++) cin >> v[i];
    srand(712367);
    Node* root = nullptr;
    vector<Node*> ptr(n+1, nullptr);
    // build treap
    for(int i=0;i<n;i++){
        Node* nd = new Node(v[i]);
        ptr[v[i]] = nd;
        root = merge(root, nd);
    }
    vector<pair<int,int>> moves;
    long long sumy = 0;
    for(int t = n; t >= 1; --t){
        Node* u = ptr[t];
        int idx = getIndex(u);
        if(idx == 1) continue;
        // extract u
        auto pr1 = split(root, idx-1); // [1..idx-1], [idx..]
        auto pr2 = split(pr1.second, 1); // [u], [idx+1..]
        Node* A = pr1.first;
        Node* M = pr2.first;
        Node* C = pr2.second;
        // move to front: M + A + C
        root = merge(M, merge(A, C));
        moves.emplace_back(idx, 1);
        sumy += 1;
    }
    long long m = (long long)moves.size();
    long long final_cost = (sumy + 1) * (m + 1);
    cout << final_cost << " " << moves.size() << "\n";
    for(auto &mv: moves){
        cout << mv.first << " " << mv.second << "\n";
    }
    return 0;
}