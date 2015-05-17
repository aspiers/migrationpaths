Migration path-finding algorithm
================================

Algorithm design goals
----------------------

My goals for the algorithm were as follows:

- If there is any valid migration path, the algorithm *must* find at
  least one.  There is usually a valid path, but not always; for
  example consider a protozoic cloud with two physical servers of
  16GB, each hosting a 12GB VM.  If you wanted to swap these two VMs
  around, it would be impossible (unless RAM over-committing was
  allowed).
- It should find a path which is *reasonably* optimal with respect
  to the migration cost function.  In prior work, I already tried
  Dijkstra's shortest path algorithm and demonstrated that an
  exhaustive search for the shortest path has intolerably high
  complexity.
- The migration cost function should be pluggable.  Initially it
  will simply consider the cost as proportional to the RAM footprint
  of the VM being migrated.
- For now, use a smoke-and-mirrors in-memory model of the cloud's state.
  Later, the code can be ported to consume the `nova` API.
- In light of the above, the implementation should be in Python.
- Determination of which states are sane should be pluggable.
  For example, the algorithm should not hardcode any assumptions
  about whether physical servers can over-commit CPU or RAM.

Algorithm implementation
------------------------

At first I naively thought I could simply model the problem as a graph
where each node represents an arrangement of VMs within the cloud
(i.e. a mapping of VMs to VM hosts) and each edge represents a
migration of a single VM from one host to another, and then use
[Dijkstra's shortest path
algorithm](http://en.wikipedia.org/wiki/Dijkstra%27s_algorithm) to
find the shortest sequence of migrations which transforms the starting
arrangement to the desired final arrangement.

However whilst modelling the problem as a graph path-finding problem
was valid, Dijkstra's algorithm immediately turned out to be
completely useless due to the algorithmic complexity of exploring this
graph.

I quickly realised that an approach which substantially pruned the
search tree was required.  So my next hunch was that a reasonably
optimal algorithm could be produced by roughly emulating how a human
would intuitively set about finding a migration path in their head:

1. Make a list of each VM which isn't already in its final destination.
2. For each VM in the list, try to migrate it to its final destination.
3. If its final destination is already "full", e.g. doesn't have sufficient
   free RAM to accommodate the incoming VM, then displace one of the VMs
   already there in order to make space for the incoming VM.

And in fact this yielded a working solution.  You can [see the full
details in the code](../src/aspiers.py), which is reasonably well
documented.

By using recursive functions, the displacement can be treated in the
same manner as the VM migrations in step 2.