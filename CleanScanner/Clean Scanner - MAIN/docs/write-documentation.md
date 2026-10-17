# How to write documentation

- [How to write documentation](#how-to-write-documentation)
  - [Key points](#key-points)
  - [When to write documentation](#when-to-write-documentation)
  - [Where to write docs](#where-to-write-docs)
  - [Linking docs to Claude skills](#linking-docs-to-claude-skills)
  - [Mistakes to avoid](#mistakes-to-avoid)

## Key points

- [ ] As close to the relevant code as possible
  - **Why**: easier to find at the right time, makes it more easy to think about updating it when you change your code
- [ ] Findable at the right time
  - **Why**: You want to have the doc when you need it to read it but also when you need to update it
  - **How**: Respect section ["Where to write docs"](#where-to-write-docs) and if needed, link it in the files where it could be needed
- [ ] Concise
  - **Why**: Easier to understand the main point, make sure it is read, easier to maintain
- [ ] Pretty / Engaging
  - **Why**: Easier to remember, makes you want to read it more often
  - **How**: Use markdown tables or mermaid schemas (use AI to generate them)
- [ ] Include table of contents in long docs
  - **Why**: Gives overview of the doc and enable finding the right doc quickly
  - **How**: Use extension "Markdown All in One" (yzhang.markdown-all-in-one) and its command "Create Table of Contents"
- [ ] Include good and bad examples from the code
  - **Why**: makes it easier to understand and apply
- [ ] Add a `Key points` section with the why for each point
  - **Why**: For standards, it makes them easy to apply and you can quickly check if you have performed the task proplerly
- [ ] Standard for a task include a "Common mistakes to avoid section"
  - **Why**: its in the name, to avoid the mistakes being made again

## When to write documentation

- you struggled to remember how to do something like how to test the purchase flow in preview
- you got a PR comment asking you why you wrote that code
- you wrote a hack / workaround for a complex problem

## Where to write docs

We respect the "colocation" principle that we also use for coding: the documentation should always be as close as possible to the code it documents.

**Why**:

- makes it easier to find at the right time (when you're working on the feature)
- the team will more easily think about updating it if it's right under their nose

**How**:

1. Code documentation
   - Comment right above the line of code
   - If you need to explain **WHY** the code was written if not explicit
2. Function documentation with JSDoc
3. Feature documentation next to the feature in `app/components/<feature>/` or `app/services/`
4. General dev documentation in `/docs`

## Linking docs to Claude skills

Skills (`.claude/skills/`) reference project docs via **symlinks** in their `references/` folder, pointing back to `docs/`. This keeps `docs/` as the single source of truth while giving skills clean relative paths.

**To add a doc reference to a skill:**

```bash
cd .claude/skills/<skill>/references/
ln -s ../../../../docs/<path> <filename>
```

Then use `./references/<filename>` in SKILL.md instead of `../../../docs/<path>`.

**When creating or moving a doc in `docs/`**, check if any skill symlink points to it:

```bash
grep -rl '<filename>' .claude/skills/*/references/
```

## Mistakes to avoid

- Re-write documentation of libraries

  - **why**: it can get out of date if you update the lib and chances are, the team will forget to update it
  - **solution**: link the documentation of the lib in your own docs, focus on what is specific to our app

- Explain what the code does

  - **why**: the code should be self explanatory, and explanations can be easily out of date
  - **solution**: clear variable names, extract the functions or variables that are not clearly named

- Rely too heavily on AI to generate the doc
  - **why**: by default AI generates quite verbose doc
  - **solution**: prompt it properly with this standard as example and take time to clean what he did
