#include <bits/stdc++.h>
using namespace std;

struct Node {
    int val;
    uint32_t pri;
    int sz;
    Node *l, *r, *par;
    Node(int v, uint32_t p): val(v), pri(p), sz(1), l(nullptr), r(nullptr), par(nullptr) {}
};

inline int getsz(Node* t){ return t ? t->sz : 0; }

inline void upd(Node* t){
    if(!t) return;
    t->sz = 1 + getsz(t->l) + getsz(t->r);
    if(t->l) t->l->par = t;
    if(t->r) t->r->par = t;
}

Node* merge(Node* a, Node* b){
    if(!a){ if(b) b->par = nullptr; return b; }
    if(!b){ if(a) a->par = nullptr; return a; }
    if(a->pri < b->pri){
        a->r = merge(a->r, b);
        if(a->r) a->r->par = a;
        upd(a);
        a->par = nullptr;
        return a;
    } else {
        b->l = merge(a, b->l);
        if(b->l) b->l->par = b;
        upd(b);
        b->par = nullptr;
        return b;
    }
}

void split(Node* t, int k, Node* &a, Node* &b){ // first k to a, rest to b
    if(!t){ a = b = nullptr; return; }
    if(getsz(t->l) >= k){
        split(t->l, k, a, t->l);
        if(t->l) t->l->par = t;
        upd(t);
        b = t;
        if(b) b->par = nullptr;
    } else {
        split(t->r, k - getsz(t->l) - 1, t->r, b);
        if(t->r) t->r->par = t;
        upd(t);
        a = t;
        if(a) a->par = nullptr;
    }
}

int indexOf(Node* x){
    int res = getsz(x->l) + 1;
    while(x->par){
        if(x == x->par->r){
            res += getsz(x->par->l) + 1;
        }
        x = x->par;
    }
    return res;
}

void move_x_to_y(Node* &root, int x, int y){
    if(x == y) return;
    Node *A, *B, *C, *D, *E;
    // Split at y-1: A | B
    split(root, y-1, A, B);
    // Split B at length (x - y + 1): C (y..x) | D
    split(B, x - y + 1, C, D);
    // Split C at length (x - y): E (y..x-1) | last (x)
    split(C, x - y, E, C); // now C is the single node originally at position x
    // Rotate: C followed by E
    Node* mid = merge(C, E);
    root = merge(merge(A, mid), D);
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<int> v(n+1);
    for(int i=1;i<=n;i++) cin >> v[i];

    mt19937 rng(712367);
    vector<Node*> byVal(n+1, nullptr);
    Node* root = nullptr;
    for(int i=1;i<=n;i++){
        Node* node = new Node(v[i], rng());
        byVal[v[i]] = node;
        root = merge(root, node);
    }

    auto get_pos = [&](int val)->int{
        return indexOf(byVal[val]);
    };

    // Find largest suffix [t..n] with increasing positions
    int t = n;
    int last_pos = get_pos(n);
    for(int i = n-1; i >= 1; --i){
        int p = get_pos(i);
        if(p < last_pos){
            last_pos = p;
            t = i;
        } else {
            break;
        }
    }

    vector<pair<int,int>> ops;
    long long sumy = 0;

    while(t > 1){
        int pos_t = get_pos(t);
        int pos_prev = get_pos(t-1);
        if(pos_prev < pos_t){
            t--;
            continue;
        } else {
            // move t-1 to before t
            int x = pos_prev;
            int y = pos_t;
            ops.emplace_back(x, y);
            sumy += y;
            move_x_to_y(root, x, y);
            t--;
        }
    }

    long long moves = ops.size();
    long long final_cost = (sumy + 1) * (moves + 1);
    cout << final_cost << " " << ops.size() << "\n";
    for(auto &op : ops){
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}